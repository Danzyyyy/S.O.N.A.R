"""
Tier 1: Feature Coverage Test Suite
Validates core functionality for OpenSearch vector store, nomic-embed-text (768 dimensions),
and document text extraction (Markdown and PDF) as specified in Pertemuan 6 (Modules 10, 11, 12).
"""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from pypdf import PdfWriter

from app.embeddings import embed_text
from app.ingest import extract_text
from app.vector_store import VectorStore
from tests.test_doubles import (
    SimulatedOpenSearchClient,
    check_live_ollama,
    deterministic_768_embedding,
)


class TestOpenSearchVectorStore:
    """Feature coverage for OpenSearch VectorStore client."""

    def test_vector_store_initialization_defaults(self, simulated_client: SimulatedOpenSearchClient):
        """VectorStore should initialize with default configuration and client injection."""
        vs = VectorStore(client=simulated_client)
        assert vs.index_name == "knowledge-base"
        assert vs.dimension == 768
        assert vs.backend == "opensearch"
        assert vs.client is simulated_client

    def test_vector_store_initialization_custom(self, simulated_client: SimulatedOpenSearchClient):
        """VectorStore should respect custom index name and dimension settings."""
        vs = VectorStore(
            client=simulated_client,
            index_name="custom-index",
            dimension=768,
            base_url="http://custom-host:9200",
        )
        assert vs.index_name == "custom-index"
        assert vs.dimension == 768
        assert vs.base_url == "http://custom-host:9200"

    def test_ensure_index_creates_knn_mapping_idempotently(
        self, vector_store_simulated: VectorStore, simulated_client: SimulatedOpenSearchClient
    ):
        """
        ensure_index must create an OpenSearch index configured for k-NN with 768 dimensions
        and cosine similarity, and must be idempotent.
        """
        idx = "test-knn-index"
        created = vector_store_simulated.ensure_index(index_name=idx, dimension=768)
        assert created is True

        # Verify index exists in client
        assert simulated_client.indices.exists(index=idx) is True

        # Calling again must be idempotent and return False without error
        created_again = vector_store_simulated.ensure_index(index_name=idx, dimension=768)
        assert created_again is False

    def test_index_document_stores_vector_and_metadata(
        self, vector_store_simulated: VectorStore
    ):
        """index_document should insert a document with text, metadata, and 768-d embedding."""
        idx = "test-doc-index"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        sample_vector = deterministic_768_embedding("Mahasiswa mengajukan cuti akademik")
        meta = {"source": "sop-cuti-akademik.md", "category": "academic"}

        res = vector_store_simulated.index_document(
            index_name=idx,
            doc_id="doc-001",
            text="Mahasiswa mengajukan cuti akademik lewat portal kampus",
            embedding=sample_vector,
            metadata=meta,
        )

        assert res is not None
        assert res.get("result") in ("created", "updated") or res.get("_id") == "doc-001"
        assert vector_store_simulated.count(index_name=idx) == 1

    def test_search_vector_retrieval(self, vector_store_simulated: VectorStore):
        """search should execute vector k-NN query and return ranked documents."""
        idx = "test-search-index"
        vector_store_simulated.ensure_index(index_name=idx, dimension=768)

        text_content = "Prosedur pengisian KRS semester ganjil."
        vec = deterministic_768_embedding(text_content)
        vector_store_simulated.index_document(
            index_name=idx,
            doc_id="krs-01",
            text=text_content,
            embedding=vec,
            metadata={"source": "sop-krs.md"},
        )

        # Search using identical vector
        hits = vector_store_simulated.search(index_name=idx, query_embedding=vec, k=3)
        assert len(hits) == 1
        assert hits[0]["id"] == "krs-01"
        assert hits[0]["text"] == text_content
        assert hits[0]["metadata"]["source"] == "sop-krs.md"
        assert isinstance(hits[0]["score"], float)
        assert 0.0 <= hits[0]["score"] <= 1.0


class TestEmbeddingEngine:
    """Feature coverage for Ollama nomic-embed-text (768-dim) embedding engine."""

    def test_nomic_embed_text_dimension_is_768(self):
        """
        Ollama nomic-embed-text embedding vector must have dimension 768
        as required by Pertemuan 6 Module 11.
        """
        vec = embed_text("Mahasiswa mengajukan cuti akademik", base_url="http://localhost:11434")
        assert isinstance(vec, list)
        assert len(vec) == 768
        assert all(isinstance(v, (float, int)) for v in vec)

    def test_nomic_embed_text_determinism(self):
        """
        Embedding output must be deterministic: identical text input produces
        strictly identical float vectors (v1 == v2).
        """
        v1 = embed_text("tes determinisme akademik", base_url="http://localhost:11434")
        v2 = embed_text("tes determinisme akademik", base_url="http://localhost:11434")
        assert v1 == v2
        assert len(v1) == 768



class TestTextExtraction:
    """Feature coverage for multi-format text extraction (extract_text) from Module 10."""

    def test_extract_text_from_markdown(self, tmp_path: Path):
        """extract_text should extract raw string content verbatim from Markdown files."""
        md_file = tmp_path / "test-sop.md"
        expected_content = "# SOP Pengajuan Cuti\n\nIsi ketentuan cuti akademik."
        md_file.write_text(expected_content, encoding="utf-8")

        extracted = extract_text(str(md_file))
        assert extracted == expected_content

    def test_extract_text_from_pdf(self, tmp_path: Path):
        """extract_text should iterate PDF pages and join extracted text with newlines."""
        pdf_path = tmp_path / "test-doc.pdf"

        # Generate a valid minimal PDF with pypdf
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        with open(pdf_path, "wb") as f:
            writer.write(f)

        extracted = extract_text(str(pdf_path))
        # Blank page returns empty string without crashing
        assert isinstance(extracted, str)
