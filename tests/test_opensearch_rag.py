"""
Test Suite: OpenSearch Integration, VectorStore, Ingestion, and Invariants.
Validates Requirements R2 and R3 from Pertemuan 6 (Modules 10, 11, 12).
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ingest import extract_text, ingest_knowledge_base
from app.main import app
from app.vector_store import VectorStore


@pytest.fixture
def test_client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# =====================================================================
# 1. Knowledge Base & Text Extraction Tests (Module 10)
# =====================================================================

def test_extract_text_markdown():
    """Memverifikasi fungsi extract_text dapat membaca file markdown SOP."""
    cuti_path = os.path.join("knowledge-base", "sop-cuti-akademik.md")
    assert os.path.exists(cuti_path), f"File {cuti_path} tidak ditemukan"
    content = extract_text(cuti_path)
    assert len(content) > 100
    assert "Tujuan" in content
    assert "Syarat Umum" in content
    assert "Tahapan Proses" in content
    assert "Dokumen yang Diperlukan" in content
    assert "Estimasi Waktu" in content


def test_sop_cuti_akademik_has_five_required_sections():
    """Memverifikasi 5 bagian wajib pada SOP Cuti Akademik."""
    cuti_path = os.path.join("knowledge-base", "sop-cuti-akademik.md")
    content = extract_text(cuti_path)
    for section in ["Tujuan", "Syarat Umum", "Tahapan Proses", "Dokumen yang Diperlukan", "Estimasi Waktu"]:
        assert section.lower() in content.lower(), f"Bagian '{section}' hilang pada sop-cuti-akademik.md"


def test_sop_pendaftaran_krs_has_five_required_sections_and_ips_formulas():
    """Memverifikasi 5 bagian wajib dan formula SKS berbasis IPS pada SOP KRS."""
    krs_path = os.path.join("knowledge-base", "sop-pendaftaran-krs.md")
    assert os.path.exists(krs_path), f"File {krs_path} tidak ditemukan"
    content = extract_text(krs_path)
    for section in ["Tujuan", "Syarat Umum", "Tahapan Proses", "Dokumen yang Diperlukan", "Estimasi Waktu"]:
        assert section.lower() in content.lower(), f"Bagian '{section}' hilang pada sop-pendaftaran-krs.md"

    # Verifikasi formula IPS
    assert "IPS >= 3.00" in content
    assert "24 SKS" in content
    assert "Masa Perubahan Rencana Studi" in content or "PRS" in content


# =====================================================================
# 2. VectorStore OpenSearch Interface Tests (Module 12)
# =====================================================================

def test_vector_store_initialization():
    """Memverifikasi inisialisasi default VectorStore."""
    vs = VectorStore(base_url="http://localhost:9200", index_name="test-index", dimension=768)
    assert vs.base_url == "http://localhost:9200"
    assert vs.index_name == "test-index"
    assert vs.dimension == 768


def test_vector_store_ensure_index_creates_knn_mapping():
    """Memverifikasi ensure_index membuat struktur mapping k-NN OpenSearch yang benar."""
    mock_client = MagicMock()
    mock_client.indices.exists.return_value = False
    mock_client.indices.create.return_value = {"acknowledged": True}

    vs = VectorStore(base_url="http://localhost:9200", client=mock_client, dimension=768)
    created = vs.ensure_index("custom-index")

    assert created is True
    mock_client.indices.exists.assert_called_once_with(index="custom-index")
    mock_client.indices.create.assert_called_once()

    call_args = mock_client.indices.create.call_args[1]
    assert call_args["index"] == "custom-index"
    body = call_args["body"]

    # Validasi settings k-NN
    assert body["settings"]["index"]["knn"] is True
    assert body["settings"]["index"]["number_of_replicas"] == 0

    # Validasi mapping k-NN HNSW
    props = body["mappings"]["properties"]
    assert props["text"]["type"] == "text"
    assert props["embedding"]["type"] == "knn_vector"
    assert props["embedding"]["dimension"] == 768
    assert props["embedding"]["method"]["name"] == "hnsw"
    assert props["embedding"]["method"]["space_type"] == "cosinesimil"
    assert props["embedding"]["method"]["engine"] == "nmslib"


def test_vector_store_ensure_index_idempotency():
    """Memverifikasi ensure_index mengembalikan False jika index sudah ada."""
    mock_client = MagicMock()
    mock_client.indices.exists.return_value = True

    vs = VectorStore(base_url="http://localhost:9200", client=mock_client)
    created = vs.ensure_index("existing-index")

    assert created is False
    mock_client.indices.create.assert_not_called()


def test_vector_store_index_document():
    """Memverifikasi operasi index_document menyimpan payload dan embedding ke OpenSearch."""
    mock_client = MagicMock()
    mock_client.index.return_value = {"_id": "doc-1", "result": "created"}

    vs = VectorStore(base_url="http://localhost:9200", client=mock_client)
    sample_embedding = [0.1] * 768
    res = vs.index_document(
        index_name="knowledge-base",
        doc_id="doc-1",
        text="Mahasiswa mengajukan cuti akademik lewat portal kampus",
        embedding=sample_embedding,
        metadata={"source": "sop-cuti-akademik.md"},
    )

    assert res["result"] == "created"
    mock_client.index.assert_called_once()
    kwargs = mock_client.index.call_args[1]
    assert kwargs["index"] == "knowledge-base"
    assert kwargs["id"] == "doc-1"
    assert kwargs["body"]["text"] == "Mahasiswa mengajukan cuti akademik lewat portal kampus"
    assert kwargs["body"]["embedding"] == sample_embedding
    assert kwargs["body"]["metadata"]["source"] == "sop-cuti-akademik.md"
    assert kwargs["refresh"] is True


def test_vector_store_search_knn_query():
    """Memverifikasi pembentukan k-NN search query payload dan parsing hasil hits."""
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "sop-cuti",
                    "_score": 0.887,
                    "_source": {
                        "text": "Mahasiswa mengajukan cuti akademik",
                        "metadata": {"source": "sop-cuti-akademik.md"},
                    },
                }
            ]
        }
    }

    vs = VectorStore(base_url="http://localhost:9200", client=mock_client)
    query_vector = [0.05] * 768
    hits = vs.search(index_name="knowledge-base", query_embedding=query_vector, k=3)

    assert len(hits) == 1
    assert hits[0]["id"] == "sop-cuti"
    assert hits[0]["score"] == 0.887
    assert hits[0]["text"] == "Mahasiswa mengajukan cuti akademik"
    assert hits[0]["metadata"]["source"] == "sop-cuti-akademik.md"

    # Periksa query DSL k-NN
    search_kwargs = mock_client.search.call_args[1]
    body = search_kwargs["body"]
    assert body["size"] == 3
    assert body["query"]["knn"]["embedding"]["vector"] == query_vector
    assert body["query"]["knn"]["embedding"]["k"] == 3


# =====================================================================
# 3. Ingestion Pipeline Tests
# =====================================================================

def test_ingest_knowledge_base_pipeline():
    """Memverifikasi pemanggilan fungsi ingest_knowledge_base memproses file dan mengindeks."""
    mock_vs = MagicMock()
    mock_vs.ensure_index.return_value = True
    mock_vs.index_document.return_value = {"result": "created"}

    dummy_embedding = [0.01] * 768
    with patch("app.ingest.embed_text", return_value=dummy_embedding):
        count = ingest_knowledge_base(
            kb_path="knowledge-base",
            vector_store=mock_vs,
            base_url="http://ollama:11434",
            index_name="knowledge-base",
        )

    # Direktori knowledge-base memiliki minimal 5 file SOP
    assert count >= 2
    assert mock_vs.ensure_index.called
    assert mock_vs.index_document.call_count == count


# =====================================================================
# 4. Critical API Invariant Tests & Regression Gates
# =====================================================================

def test_chat_stream_empty_messages_returns_400(test_client):
    """
    CRITICAL INVARIANT TEST:
    POST /chat/stream dengan body {"messages": []} WAJIB menghasilkan HTTP 400 Bad Request.
    """
    response = test_client.post("/chat/stream", json={"messages": []})
    assert response.status_code == 400, f"Diharapkan 400 tapi diperoleh {response.status_code}"
    data = response.json()
    assert "messages kosong" in data.get("detail", "").lower()


def test_api_chat_stream_empty_messages_returns_400(test_client):
    """Memverifikasi endpoint alias /api/chat/stream juga mengembalikan HTTP 400 pada messages kosong."""
    response = test_client.post("/api/chat/stream", json={"messages": []})
    assert response.status_code == 400
    assert "messages kosong" in response.json().get("detail", "").lower()


def test_api_chat_empty_messages_returns_400(test_client):
    """Memverifikasi endpoint sinkron /api/chat juga mengembalikan HTTP 400 pada messages kosong."""
    response = test_client.post("/api/chat", json={"messages": []})
    assert response.status_code == 400
    assert "messages kosong" in response.json().get("detail", "").lower()


def test_api_search_missing_query_returns_400(test_client):
    """Memverifikasi /api/search mengembalikan HTTP 400 jika parameter query tidak disertakan."""
    response = test_client.post("/api/search", json={})
    assert response.status_code in (400, 422)


def test_health_check_endpoint(test_client):
    """Memverifikasi endpoint /health mengembalikan status komprehensif termasuk Ollama dan OpenSearch."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ollama_status" in data
    assert "opensearch_status" in data
    assert "configured_model" in data
    assert "available_models" in data


def test_api_search_success_with_mocked_vector_store(test_client):
    """Memverifikasi /api/search mengembalikan struktur hits ketika query diberikan."""
    mock_hits = [
        {
            "id": "sop-cuti-1",
            "score": 0.92,
            "text": "Mahasiswa mengajukan cuti akademik lewat portal kampus",
            "metadata": {"source": "sop-cuti-akademik.md"}
        }
    ]
    with patch("app.main.embed_text", return_value=[0.1] * 768), \
         patch.object(VectorStore, "search", return_value=mock_hits):
        res = test_client.post("/api/search", json={"query": "bagaimana cara izin tidak kuliah", "k": 1})
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "bagaimana cara izin tidak kuliah"
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "sop-cuti-1"
        assert data["results"][0]["score"] == 0.92
        assert "portal kampus" in data["results"][0]["text"]


def test_chat_stream_valid_message_with_mocked_ollama(test_client):
    """Memverifikasi streaming SSE berfungsi ketika pesan valid diberikan."""
    mock_lines = [
        b'{"message": {"content": "Halo,"}, "done": false}',
        b'{"message": {"content": " ada yang bisa dibantu?"}, "done": true}'
    ]

    class MockAsyncResponse:
        async def aiter_lines(self):
            for line in mock_lines:
                yield line.decode("utf-8")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockAsyncClient:
        def stream(self, method, url, **kwargs):
            return MockAsyncResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.main.httpx.AsyncClient", return_value=MockAsyncClient()):
        res = test_client.post("/chat/stream", json={"message": "Halo S.O.N.A.R"})
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        text = res.text
        assert "data:" in text
        assert "Halo," in text


def test_docker_compose_config_executes_cleanly():
    """Memverifikasi file docker-compose.yml lolos validasi 'docker compose config' tanpa sintaks error."""
    import subprocess
    result = subprocess.run(
        ["docker", "compose", "config"],
        cwd=".",
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"docker compose config error: {result.stderr}"
    assert "opensearch:" in result.stdout
    assert "opensearch-dashboards:" in result.stdout
    assert "2.11.0" in result.stdout
