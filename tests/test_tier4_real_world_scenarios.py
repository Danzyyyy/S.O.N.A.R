"""
Tier 4: Real-World Scenarios Test Suite
Validates production real-world use cases, Pertemuan 6 academic verification queries,
and strict API invariant regressions (POST /chat/stream HTTP 400 on empty messages).
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.ingest import extract_text, ingest_knowledge_base
from app.main import app
from app.vector_store import VectorStore
from tests.test_doubles import (
    SimulatedOpenSearchClient,
    deterministic_768_embedding,
)


class TestRealWorldAcademicScenarios:
    """Real-world scenarios verifying domain queries against Pertemuan 6 SOPs."""

    @pytest.fixture(autouse=True)
    def setup_real_knowledge_base(self, vector_store_simulated: VectorStore):
        """Indexes real knowledge-base files present in repo for realistic validation."""
        self.vs = vector_store_simulated
        self.idx_name = "real-world-sop-index"
        self.vs.ensure_index(index_name=self.idx_name, dimension=768)

        kb_path = Path("knowledge-base")
        if kb_path.exists():
            for sop_file in kb_path.glob("*.md"):
                content = extract_text(str(sop_file)).strip()
                if content:
                    doc_id = sop_file.stem
                    vec = deterministic_768_embedding(content)
                    self.vs.index_document(
                        index_name=self.idx_name,
                        doc_id=doc_id,
                        text=content,
                        embedding=vec,
                        metadata={
                            "source": sop_file.name,
                            "path": str(sop_file),
                        },
                    )

    def test_pertemuan_6_academic_leave_verification_query(self):
        """
        Pertemuan 6 Real-World Verification Query:
        Query: 'bagaimana cara izin tidak kuliah satu semester'
        Expected Outcome:
        1. Top retrieved document is 'sop-cuti-akademik'.
        2. Document text contains all 5 mandatory sections:
           - Tujuan
           - Syarat Umum
           - Tahapan Proses
           - Dokumen yang Diperlukan
           - Estimasi Waktu
        3. Document contains operational procedures: 'portal kampus', 'Dosen Pembimbing Akademik' (DPA).
        """
        query = "bagaimana cara izin tidak kuliah satu semester"
        q_vec = deterministic_768_embedding(query)

        hits = self.vs.search(index_name=self.idx_name, query_embedding=q_vec, k=3)
        assert len(hits) > 0, "Expected non-empty search results"

        top_hit = hits[0]
        assert "cuti" in top_hit["id"].lower() or "cuti" in top_hit["metadata"].get("source", "").lower()

        text = top_hit["text"]
        # Mandatory Section 1: Tujuan
        assert "Tujuan" in text, "Missing mandatory section: Tujuan"
        # Mandatory Section 2: Syarat Umum
        assert "Syarat Umum" in text, "Missing mandatory section: Syarat Umum"
        # Mandatory Section 3: Tahapan Proses
        assert "Tahapan Proses" in text, "Missing mandatory section: Tahapan Proses"
        # Mandatory Section 4: Dokumen yang Diperlukan
        assert "Dokumen yang Diperlukan" in text, "Missing mandatory section: Dokumen yang Diperlukan"
        # Mandatory Section 5: Estimasi Waktu
        assert "Estimasi Waktu" in text, "Missing mandatory section: Estimasi Waktu"

        # Domain operational keywords
        assert "portal kampus" in text.lower()
        assert "dosen pembimbing akademik" in text.lower() or "dpa" in text.lower()

    def test_krs_registration_verification_query(self):
        """
        Real-world query for study plan registration and credit limit rules:
        Query: 'bagaimana prosedur pengisian kartu rencana studi dan batas sks'
        Expected Outcome:
        1. Top retrieved document is 'sop-pendaftaran-krs'.
        2. Document text contains all 5 mandatory sections.
        3. Covers SKS credit limit formulas based on IPS.
        """
        query = "bagaimana prosedur pengisian kartu rencana studi dan batas sks"
        q_vec = deterministic_768_embedding(query)

        hits = self.vs.search(index_name=self.idx_name, query_embedding=q_vec, k=3)
        assert len(hits) > 0

        top_hit = hits[0]
        assert "krs" in top_hit["id"].lower() or "krs" in top_hit["metadata"].get("source", "").lower()

        text = top_hit["text"]
        # Validate 5 mandatory sections
        for section in ["Tujuan", "Syarat Umum", "Tahapan Proses", "Dokumen yang Diperlukan", "Estimasi Waktu"]:
            assert section in text, f"Missing section '{section}' in KRS SOP"

        # Validate IPS credit threshold mentioned
        assert "sks" in text.lower()
        assert "ips" in text.lower()


class TestApiInvariants:
    """
    API Invariants & Regression Protections.
    Strictly guarantees that POST /chat/stream returns HTTP 400 Bad Request
    when messages is empty as mandated by Pertemuan 6 Canary Checks.
    """

    def test_api_invariant_empty_messages_array_returns_http_400(self, api_test_client: TestClient):
        """
        Canary Regression Test:
        POST /chat/stream with payload {"messages": []} must return HTTP status 400
        and detail message 'messages kosong'.
        """
        response = api_test_client.post(
            "/chat/stream",
            json={"messages": []},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "messages kosong" in data.get("detail", "")

    def test_api_invariant_alias_endpoint_empty_messages_returns_http_400(self, api_test_client: TestClient):
        """
        Canary Regression Test on alias path:
        POST /api/chat/stream with {"messages": []} must return HTTP 400.
        """
        response = api_test_client.post(
            "/api/chat/stream",
            json={"messages": []},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "messages kosong" in response.json().get("detail", "")

    def test_api_invariant_empty_string_message_returns_http_400(self, api_test_client: TestClient):
        """
        Payload with empty message string or null messages must return HTTP 400.
        """
        response = api_test_client.post(
            "/chat/stream",
            json={"message": ""},
        )
        assert response.status_code == 400
        assert "messages kosong" in response.json().get("detail", "")

        response_null = api_test_client.post(
            "/chat/stream",
            json={},
        )
        assert response_null.status_code == 400
        assert "messages kosong" in response_null.json().get("detail", "")

    def test_api_invariant_chat_endpoint_empty_messages_returns_http_400(self, api_test_client: TestClient):
        """
        Standard non-streaming POST /api/chat must also return HTTP 400 on empty messages.
        """
        response = api_test_client.post(
            "/api/chat",
            json={"messages": []},
        )
        assert response.status_code == 400
        assert "messages kosong" in response.json().get("detail", "")

    def test_api_invariant_valid_messages_does_not_return_400(self, api_test_client: TestClient, monkeypatch):
        """
        A valid message array must NOT return HTTP 400.
        """
        # Patch Ollama chat stream to return a valid dummy SSE response if offline
        from tests.test_doubles import check_live_ollama

        valid_payload = {
            "messages": [{"role": "user", "content": "Halo, apa kabar?"}],
            "temperature": 0.2,
        }

        response = api_test_client.post(
            "/chat/stream",
            json=valid_payload,
        )

        # Status must not be 400
        assert response.status_code != 400
        # Valid stream returns 200 text/event-stream
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
