"""
Tier 3: Cross-Feature Integration Test Suite
Validates the interconnected pipeline:
Document Ingest (extract_text) -> Dense Embedding (embed_text, 768-d) -> OpenSearch VectorStore -> k-NN Retrieval
Verifies semantic ranking discrimination, multi-index isolation, and document updates.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from app.ingest import ingest_knowledge_base
from app.vector_store import VectorStore
from tests.test_doubles import (
    SimulatedOpenSearchClient,
    deterministic_768_embedding,
)


class TestCrossFeatureIntegration:
    """Integration verification across ingestion, vector storage, and semantic retrieval."""

    def test_end_to_end_knowledge_base_ingestion_pipeline(
        self, temp_kb_dir: Path, vector_store_simulated: VectorStore
    ):
        """
        Ingest pipeline should read directory files (.md/.pdf), extract text,
        generate 768-d embeddings, and index them into OpenSearch.
        """
        idx = "integration-kb-docs"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        total_ingested = ingest_knowledge_base(
            kb_path=str(temp_kb_dir),
            vector_store=vector_store_simulated,
            index_name=idx,
        )

        assert total_ingested >= 2, f"Expected at least 2 documents ingested, got {total_ingested}"
        assert vector_store_simulated.count(index_name=idx) >= 2

        # Verify both documents are searchable in the index
        cuti_hits = vector_store_simulated.search(
            index_name=idx,
            query_embedding=deterministic_768_embedding("cuti akademik"),
            k=2,
        )
        assert len(cuti_hits) > 0
        hit_sources = [h["metadata"].get("source") for h in cuti_hits]
        assert "sop-cuti-akademik.md" in hit_sources

    def test_semantic_ranking_discrimination_between_sops(
        self, vector_store_simulated: VectorStore
    ):
        """
        Verifies that k-NN vector search discriminates between distinct domain SOPs:
        - Query about academic leave ranks sop-cuti-akademik as #1.
        - Query about KRS / SKS credits ranks sop-pendaftaran-krs as #1.
        - Query about cybersecurity incident ranks sop-investigasi-insiden as #1.
        """
        idx = "integration-ranking"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        # 1. Cuti Akademik SOP
        text_cuti = (
            "SOP Cuti Akademik: Mahasiswa mengajukan permohonan penghentian studi sementara lewat portal kampus. "
            "Syarat minimal 2 semester aktif dan bebas tanggungan perpustakaan serta UKT."
        )
        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="sop-cuti",
            text=text_cuti,
            embedding=deterministic_768_embedding(text_cuti),
            metadata={"source": "sop-cuti-akademik.md", "topic": "cuti"},
        )

        # 2. KRS SOP
        text_krs = (
            "SOP Pendaftaran KRS: Mahasiswa memilih mata kuliah pada kartu rencana studi online. "
            "Batas beban SKS maksimal 24 ditentukan berdasarkan Indeks Prestasi Semester (IPS) dengan approval DPA."
        )
        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="sop-krs",
            text=text_krs,
            embedding=deterministic_768_embedding(text_krs),
            metadata={"source": "sop-pendaftaran-krs.md", "topic": "krs"},
        )

        # 3. Insiden Investigasi SOP
        text_insiden = (
            "SOP Investigasi Insiden: Prosedur penanganan insiden keamanan siber dan peretasan sistem informasi. "
            "Isolasi jaringan, analisa forensik log server, dan mitigasi eskalasi ancaman."
        )
        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="sop-insiden",
            text=text_insiden,
            embedding=deterministic_768_embedding(text_insiden),
            metadata={"source": "sop-investigasi-insiden.md", "topic": "security"},
        )

        # Query A: Cuti
        q_cuti_vec = deterministic_768_embedding("bagaimana cara izin tidak kuliah satu semester")
        hits_cuti = vector_store_simulated.search(index_name=idx, query_embedding=q_cuti_vec, k=3)
        assert hits_cuti[0]["id"] == "sop-cuti"
        assert hits_cuti[0]["metadata"]["topic"] == "cuti"

        # Query B: KRS
        q_krs_vec = deterministic_768_embedding("aturan pemilihan mata kuliah dan batas maksimal sks berdasarkan ips")
        hits_krs = vector_store_simulated.search(index_name=idx, query_embedding=q_krs_vec, k=3)
        assert hits_krs[0]["id"] == "sop-krs"
        assert hits_krs[0]["metadata"]["topic"] == "krs"

        # Query C: Insiden Keamanan
        q_insiden_vec = deterministic_768_embedding("penanganan peretasan server dan investigasi ancaman siber")
        hits_insiden = vector_store_simulated.search(index_name=idx, query_embedding=q_insiden_vec, k=3)
        assert hits_insiden[0]["id"] == "sop-insiden"
        assert hits_insiden[0]["metadata"]["topic"] == "security"

    def test_multi_index_isolation(self, vector_store_simulated: VectorStore):
        """Documents indexed into one index must not leak or be visible in another index."""
        idx_alpha = "isolation-alpha"
        idx_beta = "isolation-beta"

        vector_store_simulated.ensure_index(index_name=idx_alpha, dimension=768)
        vector_store_simulated.ensure_index(index_name=idx_beta, dimension=768)

        vec = deterministic_768_embedding("Konten rahasia Alpha")
        vector_store_simulated.index_document(
            index_name=idx_alpha,
            doc_id="alpha-01",
            text="Konten rahasia Alpha",
            embedding=vec,
            metadata={"env": "alpha"},
        )

        # Search in idx_alpha should return 1 hit
        hits_alpha = vector_store_simulated.search(index_name=idx_alpha, query_embedding=vec, k=3)
        assert len(hits_alpha) == 1
        assert hits_alpha[0]["id"] == "alpha-01"

        # Search in idx_beta must return 0 hits
        hits_beta = vector_store_simulated.search(index_name=idx_beta, query_embedding=vec, k=3)
        assert len(hits_beta) == 0

    def test_document_upsert_idempotence(self, vector_store_simulated: VectorStore):
        """Re-indexing a document with identical doc_id updates text and embedding in place."""
        idx = "integration-upsert"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        doc_id = "doc-update"
        vec_v1 = deterministic_768_embedding("Versi 1 teks dokumen.")
        vector_store_simulated.index_document(
            index_name=idx,
            doc_id=doc_id,
            text="Versi 1 teks dokumen.",
            embedding=vec_v1,
            metadata={"version": 1},
        )
        assert vector_store_simulated.count(index_name=idx) == 1

        # Re-index same ID with updated content
        vec_v2 = deterministic_768_embedding("Versi 2 teks dokumen terbaru.")
        vector_store_simulated.index_document(
            index_name=idx,
            doc_id=doc_id,
            text="Versi 2 teks dokumen terbaru.",
            embedding=vec_v2,
            metadata={"version": 2},
        )
        # Total count remains 1
        assert vector_store_simulated.count(index_name=idx) == 1

        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec_v2, k=1)
        assert len(hits) == 1
        assert hits[0]["text"] == "Versi 2 teks dokumen terbaru."
        assert hits[0]["metadata"]["version"] == 2
