# Project: PDS Pertemuan 6 & OpenSearch Integration

## Architecture
- **Host / Container Environment**: Docker Compose orchestrating `opensearch` (2.11.0), `opensearch-dashboards` (2.11.0), `ollama` (embedding & chat models), and `api` (FastAPI backend).
- **Embedding Subsystem**: Ollama model `nomic-embed-text` generating 768-dimensional dense vectors via `app/embeddings.py` calling `/api/embed`.
- **Vector Store Subsystem**: OpenSearch with k-NN plugin (`index.knn: true`, engine `nmslib`/`lucene`, space `cosinesimil`, dimension 768) managed through `app/vector_store.py` (`VectorStore` class). Dual-backend abstraction supports both OpenSearch and ChromaDB.
- **Knowledge Base Subsystem**: Markdown and PDF SOPs in `knowledge-base/` ingested via `app/ingest.py` (`extract_text` + document embedding).
- **Application & API Subsystem**: FastAPI service (`app/main.py`) exposing chat, query retrieval, and health endpoints, strictly preserving HTTP 400 regression check for empty message arrays.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | OpenSearch Risk Analysis Report | Comprehensive markdown analysis of RAM, CPU, storage, operations, maintenance, and 7-way vector store comparison | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Docker Compose OpenSearch Setup | Local single-node OpenSearch 2.11.0 & Dashboards configuration with memory limits, persistent volumes, and API service link | M2 | Pertemuan 6 Mod 12, §R3 |
| 3 | Python OpenSearch Client Integration | Dependency update (`opensearch-py`) and `VectorStore` client class with `ensure_index`, `index_document`, `search` | M2, M3 | Pertemuan 6 Mod 12, §R3 |
| 4 | Pertemuan 6 Knowledge Base SOPs | Seed SOPs (`sop-cuti-akademik.md`, `sop-pendaftaran-krs.md`) with 5 mandatory sections | M3 | Pertemuan 6 Mod 10, §R2 |
| 5 | OpenSearch Document Ingestion | Ingestion script extracting text, generating 768-d vectors via Ollama, and bulk/single indexing into OpenSearch | M3 | Pertemuan 6 Mod 10 & 12, §R3 |
| 6 | OpenSearch Semantic Retrieval & Query | k-NN vector search returning top matching documents for natural language queries (zero-keyword overlap test) | M3 | Pertemuan 6 Mod 12, §R3 |
| 7 | Invariant & Regression Protection | Preservation of POST `/chat/stream` returning 400 on empty messages and verification of vector determinism | M3, M4 | Pertemuan 6 Mod 11 & 12 |
| 8 | End-to-End Verification & Forensic Audit | Verification test harness, reviewer approval, empirical challenger validation, and clean forensic audit | M4 | System Specification |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Risk Analysis Report | Generate comprehensive `OPENSEARCH_RISK_ANALYSIS.md` covering all R1 criteria | none | DONE |
| M2 | Infrastructure & Dependencies | Configure `docker-compose.yml` for OpenSearch 2.11.0 + Dashboards, update `requirements.txt` | none | DONE |
| M3 | Pertemuan 6 & Pipeline Integration | Knowledge base SOPs, `app/vector_store.py`, ingestion script, query pipeline adaptation | M2 | DONE |
| M4 | E2E Verification & Forensic Audit | E2E testing suite, Challenger stress testing, and Forensic Integrity Audit | M1, M3 | DONE |

## Interface Contracts
### `app.embeddings.embed_text(text: str, base_url: str, model: str = "nomic-embed-text") -> list[float]`
- Input: `text` string, `base_url` Ollama endpoint.
- Output: List of 768 floating point numbers.
- Error handling: Raises `RuntimeError` or `httpx.HTTPError` on communication failure.

### `app.vector_store.VectorStore`
- `ensure_index(index_name: str = "knowledge-base", dimension: int = 768) -> bool`: Idempotently creates k-NN index with cosine similarity.
- `index_document(index_name: str, doc_id: str, text: str, embedding: list[float], metadata: dict) -> dict`: Stores document text, metadata, and 768-d embedding.
- `search(index_name: str, query_embedding: list[float], k: int = 3) -> list[dict]`: Executes k-NN query returning top k documents with `id`, `text`, `metadata`, and `score`.

### API Invariant: POST `/chat/stream`
- Request: `{"messages": []}` -> HTTP Status: `400 Bad Request`.

## Code Layout
- `docker-compose.yml`: Multi-container definition (ollama, opensearch, opensearch-dashboards, api).
- `requirements.txt`: Python dependencies (`opensearch-py`, `pypdf`, `fastapi`, `httpx`, etc.).
- `knowledge-base/`: Directory containing source `.md` and `.pdf` files.
- `app/embeddings.py`: Ollama embedding client module.
- `app/ingest.py`: Document parser and ingestion engine.
- `app/vector_store.py`: OpenSearch vector store client abstraction.
- `app/main.py`: FastAPI server and endpoints.
- `OPENSEARCH_RISK_ANALYSIS.md`: Comprehensive risk analysis report.
- `tests/`: Integration and E2E verification tests.
