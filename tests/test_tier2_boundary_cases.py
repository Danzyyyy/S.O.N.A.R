"""
Tier 2: Boundary & Corner Cases Test Suite
Validates edge cases, input anomalies, dimensional constraints, empty payloads,
large text limits, and the Pertemuan 6 zero-keyword overlap semantic retrieval proof.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from app.ingest import extract_text
from app.vector_store import VectorStore
from tests.test_doubles import (
    RequestError,
    SimulatedOpenSearchClient,
    deterministic_768_embedding,
)


class TestBoundaryCases:
    """Boundary and corner cases for OpenSearch VectorStore and Ingest pipeline."""

    def test_empty_document_text_handling(self, tmp_path: Path, vector_store_simulated: VectorStore):
        """Empty documents and empty strings should be handled gracefully without crashing."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        extracted = extract_text(str(empty_file))
        assert extracted == ""

        # Indexing empty text should be accepted or stored cleanly
        idx = "boundary-empty-text"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)
        dummy_vec = deterministic_768_embedding("")
        res = vector_store_simulated.index_document(
            index_name=idx,
            doc_id="empty-doc",
            text="",
            embedding=dummy_vec,
            metadata={"empty": True},
        )
        assert res is not None

        # Searching should find the empty document
        hits = vector_store_simulated.search(index_name=idx, query_embedding=dummy_vec, k=1)
        assert len(hits) == 1
        assert hits[0]["text"] == ""

    def test_missing_or_empty_metadata_handling(self, vector_store_simulated: VectorStore):
        """Documents indexed with empty metadata or None should default to empty dict."""
        idx = "boundary-metadata"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)
        vec = deterministic_768_embedding("Dokumen tanpa metadata")

        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="no-meta",
            text="Dokumen tanpa metadata",
            embedding=vec,
            metadata=None,
        )

        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec, k=1)
        assert len(hits) == 1
        assert hits[0]["metadata"] == {}

    def test_malformed_vector_dimension_mismatch_on_index(self, vector_store_simulated: VectorStore):
        """
        Indexing a vector with dimension != 768 (e.g. 512, 1024, or empty [])
        must be rejected by the vector store.
        """
        idx = "boundary-malformed-dim"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        # 512 dimensions instead of 768
        malformed_512 = [0.1] * 512
        with pytest.raises((RequestError, ValueError, Exception)):
            vector_store_simulated.index_document(
                index_name=idx,
                doc_id="err-512",
                text="Teks salah dimensi",
                embedding=malformed_512,
            )

        # Empty vector []
        with pytest.raises((RequestError, ValueError, Exception)):
            vector_store_simulated.index_document(
                index_name=idx,
                doc_id="err-empty",
                text="Teks vector kosong",
                embedding=[],
            )

    def test_malformed_vector_dimension_mismatch_on_search(self, vector_store_simulated: VectorStore):
        """Searching with a query vector whose dimension != 768 must raise an error."""
        idx = "boundary-search-dim"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        malformed_query = [0.5] * 128
        with pytest.raises((RequestError, ValueError, Exception)):
            vector_store_simulated.search(index_name=idx, query_embedding=malformed_query, k=3)

    def test_search_with_none_query_vector_raises_error(self, vector_store_simulated: VectorStore):
        """Invoking search with None query_embedding must raise ValueError."""
        with pytest.raises(ValueError, match="query_embedding wajib diisi"):
            vector_store_simulated.search(query_embedding=None)

    def test_zero_overlap_semantic_search_query(self, vector_store_simulated: VectorStore):
        """
        Pertemuan 6 Module 12 Semantic Retrieval Proof:
        Query: 'bagaimana cara izin tidak kuliah satu semester'
        Target: 'Mahasiswa mengajukan cuti akademik lewat portal kampus'
        The lexical intersection between query and document is ZERO words.
        The k-NN vector search must retrieve the document with a high cosine similarity score.
        """
        idx = "boundary-zero-overlap"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        target_text = "Mahasiswa mengajukan cuti akademik lewat portal kampus"
        query_text = "bagaimana cara izin tidak kuliah satu semester"

        # Explicitly verify lexical overlap is strictly zero
        target_words = set(target_text.lower().split())
        query_words = set(query_text.lower().split())
        overlap = target_words.intersection(query_words)
        assert len(overlap) == 0, f"Lexical overlap should be zero but found: {overlap}"

        # Generate vectors and index target document
        target_vec = deterministic_768_embedding(target_text, dimension=768)
        query_vec = deterministic_768_embedding(query_text, dimension=768)

        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="test-1",
            text=target_text,
            embedding=target_vec,
            metadata={"source": "manual-test", "topic": "academic"},
        )

        # Execute semantic k-NN search
        hits = vector_store_simulated.search(index_name=idx, query_embedding=query_vec, k=1)
        assert len(hits) == 1
        assert hits[0]["id"] == "test-1"
        assert hits[0]["text"] == target_text
        # Score must be positive and indicate genuine cosine alignment
        assert hits[0]["score"] > 0.5, f"Expected cosine score > 0.5, got {hits[0]['score']}"

    def test_large_document_stress_boundary(self, vector_store_simulated: VectorStore):
        """Handles large text bodies (25,000+ characters) without buffer overflow or truncation."""
        idx = "boundary-large-doc"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        large_text = "SOP Regulasi Akademik Lengkap. " * 1000  # ~31,000 characters
        vec = deterministic_768_embedding(large_text)

        res = vector_store_simulated.index_document(
            index_name=idx,
            doc_id="large-doc-01",
            text=large_text,
            embedding=vec,
            metadata={"length": len(large_text)},
        )
        assert res is not None

        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec, k=1)
        assert len(hits) == 1
        assert len(hits[0]["text"]) == len(large_text)

    def test_special_characters_and_multilingual_handling(self, vector_store_simulated: VectorStore):
        """Handles Indonesian text with punctuation, quotes, tabs, newlines, and symbols."""
        idx = "boundary-special-chars"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        special_text = (
            "SOP §12: Pengajuan Cuti (Academic Leave) — 2026/2027!\n"
            "• Syarat: IPK ≥ 2.50 & 'Bebas Tanggungan'.\n"
            "Catatan: Biaya administrasi = Rp 0,00 (Gratis)."
        )
        vec = deterministic_768_embedding(special_text)

        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="special-doc",
            text=special_text,
            embedding=vec,
            metadata={"section": "§12"},
        )

        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec, k=1)
        assert len(hits) == 1
        assert hits[0]["text"] == special_text
        assert hits[0]["metadata"]["section"] == "§12"
