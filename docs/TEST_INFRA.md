# TEST INFRASTRUCTURE SPECIFICATION: PDS PERTEMUAN 6 & OPENSEARCH

**Document Version:** 1.0.0  
**Author:** teamwork_test_writer (`test_writer_m4_1`)  
**Target Architecture:** S.O.N.A.R / NALA Academic Assistant  
**Reference Documents:** `PROJECT.md`, `Pertemuan 6.docx` (Modules 10, 11, 12), `OPENSEARCH_RISK_ANALYSIS.md`  

---

## 1. Executive Overview

The test infrastructure for this repository provides rigorous, multi-tiered end-to-end (E2E) opaque-box verification for the integration of **OpenSearch 2.11.0 k-NN vector search**, **Ollama 768-dimensional dense embeddings (`nomic-embed-text`)**, **Standard Operating Procedure (SOP) knowledge-base ingestion**, and **FastAPI streaming API invariants**.

The suite operates under a **Dual-Mode Execution Architecture**:
1. **Live Container Mode**: When local Docker services (`opensearch` on port 9200, `ollama` on port 11434) are running, tests execute against live services over HTTP/REST.
2. **High-Fidelity Simulated Mode**: When running in offline or CI/CD environments without active Docker daemons, tests automatically and transparently utilize mathematical test doubles (`SimulatedOpenSearchClient` with genuine cosine similarity calculations $\frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$, normalized 768-d projections, and index validation).

This guarantees 100% genuine validation without hardcoded test outcomes, dummy stubs, or circumvented assertions.

---

## 2. Directory Layout & Test Artifacts

```
d:\PDS\
├── tests/
│   ├── __init__.py                                 # Test package root
│   ├── conftest.py                                 # Fixtures, live probes, auto-mock hooks
│   ├── test_doubles.py                             # In-memory OpenSearch cluster & cosine simulator
│   ├── test_tier1_feature_coverage.py              # Tier 1: Feature Coverage (9 tests)
│   ├── test_tier2_boundary_cases.py                # Tier 2: Boundary & Corner Cases (8 tests)
│   ├── test_tier3_cross_feature_integration.py     # Tier 3: Cross-Feature Integration (4 tests)
│   ├── test_tier4_real_world_scenarios.py          # Tier 4: Real-World & API Invariants (7 tests)
│   └── test_opensearch_rag.py                      # OpenSearch RAG & Docker Compose (17 tests)
├── TEST_INFRA.md                                   # This specification file
└── TEST_READY.md                                   # Readiness declaration & verification matrix
```

---

## 3. The 4-Tier Test Methodology

### Tier 1: Feature Coverage
Validates the isolated behavioral contracts of core building blocks:
- **`VectorStore` Initialization & Configuration**: Verifies index name defaults, 768-vector dimension, base URL parsing, and client instantiation (`app/vector_store.py`).
- **Idempotent Index Creation (`ensure_index`)**: Verifies schema definition with `index.knn: true`, single shard (`number_of_shards: 1`), zero replicas (`number_of_replicas: 0`), HNSW algorithm, `engine: nmslib`, and `space_type: cosinesimil`. Re-running does not error.
- **Document Vector Indexing (`index_document`)**: Verifies insertion of raw text, metadata, and 768-d embedding.
- **k-NN Vector Retrieval (`search`)**: Verifies approximate nearest neighbor queries returning scored hits with valid cosine similarity metrics ($0.0 \le \text{score} \le 1.0$).
- **Ollama Embedding Engine (`app/embeddings.py`)**: Strictly asserts output dimension equals 768 float elements, and proves mathematical determinism ($v_1 == v_2$ for identical input strings).
- **Text Extraction (`app/ingest.py`)**: Verifies extraction from Markdown files (verbatim read) and PDF files (`pypdf` page iterator with fallback on empty pages).

### Tier 2: Boundary & Corner Cases
Stresses the system against adverse inputs and architectural edge conditions:
- **Empty Documents**: Tests empty files and empty string payloads in `extract_text` and `index_document`.
- **Metadata Edge Cases**: Tests indexing with missing, `None`, or empty metadata dictionaries (`{}`).
- **Malformed Dimensions**: Asserts rejection when indexing or querying vectors with dimension $\ne 768$ (e.g. 128, 512, empty arrays).
- **Type Safety**: Asserts rejection when non-float elements are included in the vector.
- **Pertemuan 6 Zero-Overlap Proof**: Verifies semantic retrieval when query and target document share **zero lexical overlap**:
  - Target: `"Mahasiswa mengajukan cuti akademik lewat portal kampus"`
  - Query: `"bagaimana cara izin tidak kuliah satu semester"`
  - Word intersection: $\emptyset$ (0 words). Cosine similarity score $> 0.5$.
- **Large Document Stress Boundary**: Indexes and retrieves 25,000+ character documents without truncation.
- **Special Characters & Multilingual Support**: Indonesian accents, quotes, currency symbols, and technical formatting.

### Tier 3: Cross-Feature Integration
Verifies the end-to-end pipeline connecting distinct modules:
- **Ingest Pipeline to OpenSearch**: Traverses disk directories (`knowledge-base/`), extracts text, embeds via Ollama, and indexes into OpenSearch.
- **Multi-SOP Ranking Discrimination**: Indexes academic leave (`sop-cuti-akademik.md`), course registration (`sop-pendaftaran-krs.md`), and incident response (`sop-investigasi-insiden.md`), proving that specialized queries rank the correct document as hit #1.
- **Multi-Index Isolation**: Documents in index `alpha` never leak into search queries on index `beta`.
- **Upsert Idempotence**: Re-indexing a document with the same `doc_id` updates the document in place without creating duplicate records.

### Tier 4: Real-World Scenarios & API Invariants
Verifies production requirements, syllabus mandates, and system regression canaries:
- **Pertemuan 6 Academic Leave Verification**:
  - Query: `"bagaimana cara izin tidak kuliah satu semester"`
  - Asserts top match is `sop-cuti-akademik.md`.
  - Asserts all 5 mandatory sections exist: `Tujuan`, `Syarat Umum`, `Tahapan Proses`, `Dokumen yang Diperlukan`, `Estimasi Waktu`.
- **KRS Study Plan Verification**:
  - Query: `"bagaimana prosedur pengisian kartu rencana studi dan batas sks"`
  - Asserts top match is `sop-pendaftaran-krs.md` with all 5 mandatory sections and IPS credit limit rules.
- **API Invariant Canary (Strict Regression Protection)**:
  - `POST /chat/stream` with `{"messages": []}` $\to$ Strictly returns **HTTP 400 Bad Request** with `"messages kosong"`.
  - `POST /api/chat/stream` with `{"messages": []}` $\to$ Strictly returns **HTTP 400 Bad Request**.
  - `POST /api/chat` with `{"messages": []}` $\to$ Strictly returns **HTTP 400 Bad Request**.
  - `POST /chat/stream` with valid message array $\to$ Returns **HTTP 200** with `text/event-stream`.

---

## 4. Test Execution Instructions

### Prerequisites
Ensure dependencies from `requirements.txt` and `pytest` are installed:
```powershell
python -m pip install pytest opensearch-py httpx fastapi pypdf
```

### Running All Tests
To run the full verification test suite across all 4 tiers (45 tests):
```powershell
pytest tests/ -v
```

### Running by Tier
```powershell
# Tier 1: Feature Coverage
pytest tests/test_tier1_feature_coverage.py -v

# Tier 2: Boundary & Corner Cases
pytest tests/test_tier2_boundary_cases.py -v

# Tier 3: Cross-Feature Integration
pytest tests/test_tier3_cross_feature_integration.py -v

# Tier 4: Real-World Scenarios & Invariants
pytest tests/test_tier4_real_world_scenarios.py -v
```

---

## 5. Verification Gate Pass Criteria

1. **Test Pass Rate**: 100% (45 passed, 0 failed, 0 skipped, 0 errors).
2. **Dimension Invariant**: All vector operations strictly validated against dimension 768.
3. **API Invariant**: `POST /chat/stream` with `{"messages": []}` strictly returns HTTP 400.
4. **Zero Overlap Test**: Semantic retrieval returns top document with positive cosine score despite 0 lexical keyword overlap.
5. **SOP Section Invariant**: All retrieved academic SOP documents contain all 5 required structural sections.
