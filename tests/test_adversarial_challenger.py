"""
Adversarial Challenger Test Suite
Empirically challenges the implementation across:
1. Zero-keyword overlap semantic retrieval & discrimination.
2. API invariant verification on POST /chat/stream & related endpoints.
3. Vector dimension mismatches, boundary edge cases, and numerical robustness.
4. Stress-testing search parameters, large payloads, and empty states.
"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.ingest import extract_text
from app.main import app
from app.vector_store import VectorStore
from tests.test_doubles import (
    NotFoundError,
    RequestError,
    SimulatedOpenSearchClient,
    SimulatedOpenSearchCluster,
    compute_cosine_similarity,
    deterministic_768_embedding,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# =============================================================================
# 1. Zero-Keyword Overlap Semantic Retrieval & Discrimination
# =============================================================================

class TestAdversarialSemanticRetrieval:
    """Stress tests semantic retrieval guarantees and zero keyword overlap."""

    def test_strict_zero_keyword_overlap_lexical_proof(self):
        """
        Mathematical proof that query and document share ZERO vocabulary tokens.
        Query: 'bagaimana cara izin tidak kuliah satu semester'
        Target: 'Mahasiswa mengajukan cuti akademik lewat portal kampus'
        """
        query_text = "bagaimana cara izin tidak kuliah satu semester"
        target_text = "Mahasiswa mengajukan cuti akademik lewat portal kampus"

        # Tokenize and normalize
        query_tokens = set(query_text.lower().split())
        target_tokens = set(target_text.lower().split())

        intersection = query_tokens.intersection(target_tokens)
        assert len(intersection) == 0, f"Lexical overlap is NOT zero: {intersection}"
        assert "cuti" not in query_tokens
        assert "akademik" not in query_tokens
        assert "izin" not in target_tokens
        assert "kuliah" not in target_tokens

    def test_semantic_retrieval_discrimination_against_distractors(self, vector_store_simulated: VectorStore):
        """
        Adversarial test: Indexes target SOP alongside 4 distraction documents.
        Validates that zero-keyword query discriminates the target with highest rank.
        """
        idx = "adversarial-discrimination-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        documents = {
            "target-cuti": "Mahasiswa mengajukan cuti akademik lewat portal kampus",
            "distractor-krs": "Prosedur pendaftaran kartu rencana studi dan pemilihan mata kuliah mahasiswa",
            "distractor-qris": "Standar operasional investigasi insiden transaksi QRIS dan rekonsiliasi merchant perbankan",
            "distractor-app": "Alur penanganan keluhan nasabah terkait aplikasi mobile banking yang mengalami crash",
            "distractor-random": "Panduan peminjaman fasilitas proyektor dan ruang rapat gedung administrasi pusat",
        }

        for doc_id, text in documents.items():
            vec = deterministic_768_embedding(text)
            vector_store_simulated.index_document(
                index_name=idx,
                doc_id=doc_id,
                text=text,
                embedding=vec,
                metadata={"category": "test", "doc_id": doc_id},
            )

        query = "bagaimana cara izin tidak kuliah satu semester"
        q_vec = deterministic_768_embedding(query)

        hits = vector_store_simulated.search(index_name=idx, query_embedding=q_vec, k=5)

        assert len(hits) == 5
        # Top hit MUST be the academic leave document
        top_hit = hits[0]
        assert top_hit["id"] == "target-cuti", f"Expected 'target-cuti' as #1, got {top_hit['id']}"
        assert "cuti akademik" in top_hit["text"]

        # Discrimination margin: top score must clearly beat all distractors
        second_hit = hits[1]
        score_diff = top_hit["score"] - second_hit["score"]
        assert score_diff > 0.05, f"Discrimination margin too low ({score_diff:.4f})"

    def test_real_knowledge_base_all_sops_zero_keyword_retrieval(self, vector_store_simulated: VectorStore):
        """
        Indexes all markdown files in knowledge-base/ and tests that
        zero-keyword query retrieves sop-cuti-akademik.md at rank #1.
        """
        idx = "adversarial-real-kb-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        kb_path = Path("knowledge-base")
        assert kb_path.exists(), "knowledge-base directory must exist"

        md_files = list(kb_path.glob("*.md"))
        assert len(md_files) >= 2, "Must contain at least 2 SOP files"

        indexed_count = 0
        for md_file in md_files:
            content = extract_text(str(md_file))
            if content.strip():
                vec = deterministic_768_embedding(content)
                vector_store_simulated.index_document(
                    index_name=idx,
                    doc_id=md_file.stem,
                    text=content,
                    embedding=vec,
                    metadata={"source": md_file.name},
                )
                indexed_count += 1

        assert indexed_count >= 2

        query = "bagaimana cara izin tidak kuliah satu semester"
        q_vec = deterministic_768_embedding(query)

        hits = vector_store_simulated.search(index_name=idx, query_embedding=q_vec, k=indexed_count)
        assert len(hits) > 0

        # Rank #1 must be sop-cuti-akademik
        top_hit = hits[0]
        assert "cuti" in top_hit["id"].lower() or "cuti" in top_hit["metadata"].get("source", "").lower()
        assert top_hit["score"] > 0.5


# =============================================================================
# 2. Critical Invariant Verification (POST /chat/stream HTTP 400)
# =============================================================================

class TestAdversarialApiInvariants:
    """Stress tests HTTP 400 invariant on empty message arrays across various payload structures."""

    @pytest.mark.parametrize("endpoint", ["/chat/stream", "/api/chat/stream", "/api/chat"])
    def test_invariant_empty_messages_list_returns_400(self, client: TestClient, endpoint: str):
        """Standard canary payload: {"messages": []} -> 400 Bad Request."""
        res = client.post(endpoint, json={"messages": []})
        assert res.status_code == 400, f"{endpoint} failed: status={res.status_code}"
        assert "messages kosong" in res.json().get("detail", "").lower()

    @pytest.mark.parametrize("endpoint", ["/chat/stream", "/api/chat/stream", "/api/chat"])
    def test_invariant_empty_dict_returns_400(self, client: TestClient, endpoint: str):
        """Empty json body: {} -> 400 Bad Request."""
        res = client.post(endpoint, json={})
        assert res.status_code == 400
        assert "messages kosong" in res.json().get("detail", "").lower()

    @pytest.mark.parametrize("endpoint", ["/chat/stream", "/api/chat/stream", "/api/chat"])
    def test_invariant_empty_string_message_returns_400(self, client: TestClient, endpoint: str):
        """Empty message field: {"message": ""} -> 400 Bad Request."""
        res = client.post(endpoint, json={"message": ""})
        assert res.status_code == 400
        assert "messages kosong" in res.json().get("detail", "").lower()

    @pytest.mark.parametrize("endpoint", ["/chat/stream", "/api/chat/stream", "/api/chat"])
    def test_invariant_empty_messages_with_nonempty_history_returns_400(self, client: TestClient, endpoint: str):
        """
        Adversarial edge case: history is present, but messages is empty.
        Must still enforce HTTP 400 invariant.
        """
        payload = {
            "messages": [],
            "history": [{"role": "user", "content": "percakapan lampau"}],
        }
        res = client.post(endpoint, json=payload)
        assert res.status_code == 400
        assert "messages kosong" in res.json().get("detail", "").lower()

    @pytest.mark.parametrize("endpoint", ["/chat/stream", "/api/chat/stream", "/api/chat"])
    def test_invariant_both_none_returns_400(self, client: TestClient, endpoint: str):
        """Explicit nulls: {"message": None, "messages": None} -> 400 Bad Request."""
        res = client.post(endpoint, json={"message": None, "messages": None})
        assert res.status_code == 400

    def test_contrast_valid_message_does_not_return_400(self, client: TestClient):
        """Contrast test: non-empty message must NOT trigger invariant HTTP 400."""
        res = client.post("/chat/stream", json={"message": "Halo S.O.N.A.R"})
        assert res.status_code != 400
        assert res.status_code == 200


# =============================================================================
# 3. Vector Dimension Mismatch & Boundary Edge Cases
# =============================================================================

class TestAdversarialVectorDimensions:
    """Stress tests dimension constraints, malformed arrays, and mathematical edge cases."""

    @pytest.mark.parametrize("bad_dim", [0, 1, 128, 512, 767, 769, 1024, 1536])
    def test_indexing_dimension_mismatch_rejected(self, vector_store_simulated: VectorStore, bad_dim: int):
        """Vectors with dimension != 768 must be rejected cleanly on indexing."""
        idx = "dim-test-index"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        bad_vec = [0.1] * bad_dim
        with pytest.raises((RequestError, ValueError, Exception)):
            vector_store_simulated.index_document(
                index_name=idx,
                doc_id=f"doc-{bad_dim}",
                text=f"Teks salah dimensi {bad_dim}",
                embedding=bad_vec,
            )

    @pytest.mark.parametrize("bad_dim", [0, 1, 128, 512, 767, 769, 1024, 1536])
    def test_searching_dimension_mismatch_rejected(self, vector_store_simulated: VectorStore, bad_dim: int):
        """Search query vectors with dimension != 768 must be rejected cleanly."""
        idx = "dim-search-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        bad_query_vec = [0.05] * bad_dim
        with pytest.raises((RequestError, ValueError, Exception)):
            vector_store_simulated.search(index_name=idx, query_embedding=bad_query_vec, k=3)

    def test_search_with_none_or_missing_embedding_raises_value_error(self, vector_store_simulated: VectorStore):
        """Query embedding set to None must raise ValueError."""
        with pytest.raises(ValueError, match="query_embedding wajib diisi"):
            vector_store_simulated.search(query_embedding=None)

    def test_indexing_missing_required_arguments_raises_value_error(self, vector_store_simulated: VectorStore):
        """Missing doc_id or text or embedding must raise ValueError."""
        with pytest.raises(ValueError, match="Parameter doc_id, text, dan embedding wajib diisi"):
            vector_store_simulated.index_document(doc_id=None, text="test", embedding=[0.1] * 768)

        with pytest.raises(ValueError, match="Parameter doc_id, text, dan embedding wajib diisi"):
            vector_store_simulated.index_document(doc_id="d1", text=None, embedding=[0.1] * 768)

        with pytest.raises(ValueError, match="Parameter doc_id, text, dan embedding wajib diisi"):
            vector_store_simulated.index_document(doc_id="d1", text="test", embedding=None)

    def test_zero_vector_cosine_handling_without_division_by_zero(self, vector_store_simulated: VectorStore):
        """
        Mathematical stress test: A zero vector [0.0]*768 has zero norm.
        The system must handle it without throwing ZeroDivisionError.
        """
        zero_vec = [0.0] * 768
        unit_vec = [1.0 / math.sqrt(768)] * 768

        # Directly test mathematical double function
        sim = compute_cosine_similarity(zero_vec, unit_vec)
        assert sim == 0.0

        sim_both_zero = compute_cosine_similarity(zero_vec, zero_vec)
        assert sim_both_zero == 0.0

    def test_non_numeric_elements_in_vector_rejected(self, vector_store_simulated: VectorStore):
        """Vectors containing strings or invalid types must be rejected."""
        idx = "non-numeric-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        corrupt_vec = [0.1] * 767 + ["not-a-number"]
        with pytest.raises((RequestError, TypeError, ValueError, Exception)):
            vector_store_simulated.index_document(
                index_name=idx,
                doc_id="corrupt-doc",
                text="Teks corrupt",
                embedding=corrupt_vec,
            )


# =============================================================================
# 4. Search Operational Boundaries & Stress Scenarios
# =============================================================================

class TestAdversarialOperationalBoundaries:
    """Stress tests edge conditions in retrieval: k limits, empty index, special chars."""

    def test_k_larger_than_indexed_document_count(self, vector_store_simulated: VectorStore):
        """Requesting k=50 on an index with only 2 documents must return 2 docs without crashing."""
        idx = "k-overshoot-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        v1 = deterministic_768_embedding("Dokumen A")
        v2 = deterministic_768_embedding("Dokumen B")

        vector_store_simulated.index_document(index_name=idx, doc_id="d-a", text="Dokumen A", embedding=v1)
        vector_store_simulated.index_document(index_name=idx, doc_id="d-b", text="Dokumen B", embedding=v2)

        hits = vector_store_simulated.search(index_name=idx, query_embedding=v1, k=50)
        assert len(hits) == 2
        assert hits[0]["id"] == "d-a"

    def test_search_empty_index_returns_empty_list(self, vector_store_simulated: VectorStore):
        """Searching an empty index returns empty list [] without error."""
        idx = "empty-index-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        q_vec = deterministic_768_embedding("Kueri sembarang")
        hits = vector_store_simulated.search(index_name=idx, query_embedding=q_vec, k=3)
        assert hits == []

    def test_document_id_with_special_characters(self, vector_store_simulated: VectorStore):
        """Doc IDs containing special characters (hyphens, dots, underscores, colons)."""
        idx = "special-id-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        special_id = "sop:cuti-akademik_v2.1@kampus#final"
        text = "SOP ID Khusus Mahasiswa"
        vec = deterministic_768_embedding(text)

        res = vector_store_simulated.index_document(
            index_name=idx,
            doc_id=special_id,
            text=text,
            embedding=vec,
        )
        assert res is not None

        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec, k=1)
        assert len(hits) == 1
        assert hits[0]["id"] == special_id

    def test_massive_text_payload_stress(self, vector_store_simulated: VectorStore):
        """Stress tests indexing and retrieval of 50,000+ character document."""
        idx = "massive-text-test"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        massive_text = "Bab SOP Akademik Komprehensif. " * 1600  # ~51,200 chars
        vec = deterministic_768_embedding(massive_text)

        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="massive-1",
            text=massive_text,
            embedding=vec,
            metadata={"char_count": len(massive_text)},
        )

        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec, k=1)
        assert len(hits) == 1
        assert len(hits[0]["text"]) == len(massive_text)
        assert hits[0]["metadata"]["char_count"] == len(massive_text)
