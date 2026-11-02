"""
Pytest configuration and fixtures for the PDS Pertemuan 6 & OpenSearch verification test suite.
Supports dual-mode execution: live against Docker OpenSearch/Ollama services if reachable,
with seamless automatic fallback to high-fidelity simulated test doubles.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.vector_store import VectorStore
from tests.test_doubles import (
    SimulatedOpenSearchClient,
    SimulatedOpenSearchCluster,
    check_live_ollama,
    check_live_opensearch,
    deterministic_768_embedding,
    mock_httpx_post,
)

# Cache connectivity once to avoid per-test socket connection timeout delays
_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OPENSEARCH_URL = os.getenv("OPENSEARCH_BASE_URL", "http://localhost:9200")
IS_OLLAMA_LIVE: bool = check_live_ollama(_OLLAMA_URL)
IS_OPENSEARCH_LIVE: bool = check_live_opensearch(_OPENSEARCH_URL)



@pytest.fixture(scope="session")
def api_test_client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture for endpoint integration testing."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def simulated_cluster() -> SimulatedOpenSearchCluster:
    """Isolated in-memory OpenSearch cluster."""
    return SimulatedOpenSearchCluster()


@pytest.fixture
def simulated_client(simulated_cluster: SimulatedOpenSearchCluster) -> SimulatedOpenSearchClient:
    """Simulated OpenSearch client instance."""
    return SimulatedOpenSearchClient(cluster=simulated_cluster)


@pytest.fixture
def vector_store_simulated(simulated_client: SimulatedOpenSearchClient) -> VectorStore:
    """VectorStore instance backed by simulated OpenSearch client."""
    vs = VectorStore(client=simulated_client, index_name="test-knowledge-base", dimension=768)
    return vs


@pytest.fixture
def vector_store_live_or_simulated(
    simulated_client: SimulatedOpenSearchClient,
) -> VectorStore:
    """
    Returns live VectorStore if local OpenSearch is available (e.g. Docker container up),
    otherwise returns simulated VectorStore.
    """
    if IS_OPENSEARCH_LIVE:
        return VectorStore(base_url=_OPENSEARCH_URL, index_name="test-knowledge-base", dimension=768)
    return VectorStore(client=simulated_client, index_name="test-knowledge-base", dimension=768)


@pytest.fixture(autouse=True)
def auto_mock_ollama_if_offline(monkeypatch):
    """
    If live Ollama is offline, intercepts httpx.Client.post for /api/embed
    so that real embed_text function executes its HTTP logic and returns 768-d vectors.
    """
    if not IS_OLLAMA_LIVE:
        orig_post = httpx.Client.post
        orig_put = httpx.Client.put

        def _patched_post(self, url, *args, **kwargs):
            url_str = str(url)
            if "/api/embed" in url_str:
                return mock_httpx_post(url, *args, **kwargs)
            if not IS_OPENSEARCH_LIVE and ":9200" in url_str:
                req = httpx.Request("POST", url)
                raise httpx.ConnectError("OpenSearch offline", request=req)
            return orig_post(self, url, *args, **kwargs)

        def _patched_put(self, url, *args, **kwargs):
            url_str = str(url)
            if not IS_OPENSEARCH_LIVE and ":9200" in url_str:
                req = httpx.Request("PUT", url)
                raise httpx.ConnectError("OpenSearch offline", request=req)
            return orig_put(self, url, *args, **kwargs)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _mock_async_stream(self, method, url, *args, **kwargs):
            class MockStreamResponse:
                async def aiter_lines(self):
                    yield '{"message": {"content": "Halo, saya asisten AI."}, "done": true}'

            yield MockStreamResponse()

        orig_async_get = httpx.AsyncClient.get
        orig_async_post = httpx.AsyncClient.post

        async def _mock_async_get(self, url, *args, **kwargs):
            url_str = str(url)
            if "/api/tags" in url_str:
                return MockHttpxResponse({"models": [{"name": "llama3.2:3b"}, {"name": "nomic-embed-text"}]}, 200)
            return await orig_async_get(self, url, *args, **kwargs)

        async def _mock_async_post(self, url, *args, **kwargs):
            url_str = str(url)
            if "/api/chat" in url_str:
                return MockHttpxResponse({"message": {"content": "Halo, saya asisten AI."}, "done": True}, 200)
            return await orig_async_post(self, url, *args, **kwargs)

        monkeypatch.setattr(httpx.Client, "post", _patched_post)
        monkeypatch.setattr(httpx.Client, "put", _patched_put)
        monkeypatch.setattr(httpx.AsyncClient, "stream", _mock_async_stream)
        monkeypatch.setattr(httpx.AsyncClient, "get", _mock_async_get)
        monkeypatch.setattr(httpx.AsyncClient, "post", _mock_async_post)







@pytest.fixture
def temp_kb_dir(tmp_path: Path) -> Path:
    """Creates a temporary knowledge-base directory with test SOP files."""
    kb_dir = tmp_path / "knowledge-base"
    kb_dir.mkdir(parents=True, exist_ok=True)

    # Sample SOP Markdown
    sop_cuti = kb_dir / "sop-cuti-akademik.md"
    sop_cuti.write_text(
        "# STANDAR OPERASIONAL PROSEDUR (SOP)\n"
        "## PROSEDUR PENGAJUAN CUTI AKADEMIK MAHASISWA\n\n"
        "### 1. Tujuan\n"
        "Standar Operasional Prosedur (SOP) ini bertujuan untuk memberikan panduan baku bagi mahasiswa yang bermaksud mengajukan cuti akademik.\n\n"
        "### 2. Syarat Umum\n"
        "1. Mahasiswa telah menempuh minimal 2 semester.\n"
        "2. Bebas tanggungan perpustakaan dan UKT.\n\n"
        "### 3. Tahapan Proses\n"
        "1. Mahasiswa mengajukan cuti akademik lewat portal kampus.\n"
        "2. Konsultasi dan persetujuan Dosen Pembimbing Akademik.\n"
        "3. Penerbitan SK Cuti Akademik oleh BAAK.\n\n"
        "### 4. Dokumen yang Diperlukan\n"
        "1. Formulir permohonan cuti akademik.\n"
        "2. Surat rekomendasi DPA.\n"
        "3. Surat bebas tanggungan perpustakaan.\n\n"
        "### 5. Estimasi Waktu\n"
        "Total estimasi waktu proses adalah 3 sampai 5 hari kerja.\n",
        encoding="utf-8",
    )

    sop_krs = kb_dir / "sop-pendaftaran-krs.md"
    sop_krs.write_text(
        "# STANDAR OPERASIONAL PROSEDUR (SOP)\n"
        "## PROSEDUR PENDAFTARAN DAN PENGISIAN KARTU RENCANA STUDI (KRS)\n\n"
        "### 1. Tujuan\n"
        "Menetapkan mekanisme dan tata cara pendaftaran serta pengesahan KRS.\n\n"
        "### 2. Syarat Umum\n"
        "1. Mahasiswa aktif dan telah melunasi UKT.\n"
        "2. Batas SKS dihitung berdasarkan IPS: IPS >= 3.00 maksimal 24 SKS.\n\n"
        "### 3. Tahapan Proses\n"
        "1. Konsultasi rencana studi bersama DPA.\n"
        "2. Pengisian KRS online di portal akademik.\n"
        "3. Persetujuan elektronik oleh DPA.\n\n"
        "### 4. Dokumen yang Diperlukan\n"
        "1. Bukti pembayaran UKT.\n"
        "2. Transkrip nilai sementara.\n"
        "3. Kartu Rencana Studi (KRS) cetak.\n\n"
        "### 5. Estimasi Waktu\n"
        "Total durasi siklus pengisian KRS adalah 5 sampai 7 hari kerja.\n",
        encoding="utf-8",
    )

    return kb_dir
