"""
OpenSearch Vector Store implementation for semantic search and k-NN retrieval.
Complies with Pertemuan 6 (Module 12) and NALA / S.O.N.A.R architecture.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    HAS_OPENSEARCH_PY = True
except ImportError:
    HAS_OPENSEARCH_PY = False

import httpx

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Client abstraction for vector database operations supporting OpenSearch (primary)
    and ChromaDB (fallback/dual-backend).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        index_name: str = "knowledge-base",
        dimension: int = 768,
        client: Any = None,
        backend: Optional[str] = None,
    ):
        self.base_url = (
            base_url or os.getenv("OPENSEARCH_BASE_URL", "http://localhost:9200")
        ).rstrip("/")
        self.index_name = index_name
        self.dimension = dimension
        self.backend = (
            backend or os.getenv("VECTOR_STORE_BACKEND", "opensearch")
        ).lower()

        self._client = client
        if self._client is None and self.backend == "opensearch" and HAS_OPENSEARCH_PY:
            self._client = self._init_opensearch_client()

    def _init_opensearch_client(self) -> OpenSearch:
        """Inisialisasi OpenSearch client resmi opensearch-py."""
        parsed = urlparse(self.base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 9200)
        use_ssl = parsed.scheme == "https"

        return OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=None,
            use_ssl=use_ssl,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
            connection_class=RequestsHttpConnection,
        )

    @property
    def client(self) -> Any:
        if self._client is None and self.backend == "opensearch" and HAS_OPENSEARCH_PY:
            self._client = self._init_opensearch_client()
        return self._client

    # -------------------------------------------------------------------------
    # Index Management
    # -------------------------------------------------------------------------

    def ensure_index(
        self,
        index_name: Optional[str] = None,
        dimension: Optional[int] = None,
    ) -> bool:
        """
        Membuat index OpenSearch dengan pengaturan k-NN vector (HNSW cosinesimil)
        secara idempoten. Mengembalikan True jika index baru dibuat, False jika sudah ada.
        """
        idx = index_name or self.index_name
        dim = dimension or self.dimension

        if self.backend == "chroma":
            return self._ensure_index_chroma(idx)

        # Coba via opensearch-py jika client tersedia
        if self.client is not None:
            try:
                if self.client.indices.exists(index=idx):
                    return False

                mapping = {
                    "settings": {
                        "index": {
                            "knn": True,
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                        }
                    },
                    "mappings": {
                        "properties": {
                            "text": {"type": "text"},
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": dim,
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimil",
                                    "engine": "nmslib",
                                },
                            },
                            "metadata": {"type": "object"},
                        }
                    },
                }
                res = self.client.indices.create(index=idx, body=mapping)
                return bool(res.get("acknowledged", True))
            except Exception as e:
                if (
                    type(e).__name__ in ("RequestError", "ValueError", "TypeError")
                    or isinstance(e, (ValueError, TypeError))
                    or (self._client is not None and not (HAS_OPENSEARCH_PY and isinstance(self._client, OpenSearch)))
                ):
                    raise
                logger.warning(
                    f"OpenSearch client ensure_index failed, attempting HTTP fallback: {e}"
                )

        # HTTP REST Fallback
        return self._ensure_index_http(idx, dim)

    def _ensure_index_http(self, idx: str, dim: int) -> bool:
        """Fallback index creation via direct HTTP REST."""
        try:
            with httpx.Client(timeout=10.0) as http_client:
                res = http_client.head(f"{self.base_url}/{idx}")
                if res.status_code == 200:
                    return False

                schema = {
                    "settings": {
                        "index": {
                            "knn": True,
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                        }
                    },
                    "mappings": {
                        "properties": {
                            "text": {"type": "text"},
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": dim,
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimil",
                                    "engine": "nmslib",
                                },
                            },
                            "metadata": {"type": "object"},
                        }
                    },
                }
                create_res = http_client.put(f"{self.base_url}/{idx}", json=schema)
                create_res.raise_for_status()
                return True
        except Exception as err:
            logger.error(f"HTTP fallback ensure_index error: {err}")
            raise

    def delete_index(self, index_name: Optional[str] = None) -> bool:
        """Menghapus index (biasanya digunakan untuk testing atau reset)."""
        idx = index_name or self.index_name
        if self.client is not None:
            try:
                if self.client.indices.exists(index=idx):
                    self.client.indices.delete(index=idx)
                    return True
                return False
            except Exception:
                pass
        try:
            with httpx.Client(timeout=10.0) as http_client:
                res = http_client.delete(f"{self.base_url}/{idx}")
                return res.status_code in (200, 204)
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Document Indexing
    # -------------------------------------------------------------------------

    def index_document(
        self,
        *args,
        index_name: Optional[str] = None,
        doc_id: Optional[str] = None,
        text: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Menyimpan dokumen dan representasi vektor embedding ke OpenSearch.
        Mendukung pemanggilan fleksibel:
        - index_document(index_name, doc_id, text, embedding, metadata)
        - index_document(doc_id, text, embedding, metadata)
        """
        # Resolusi argumen posisional
        if len(args) == 5:
            idx, d_id, txt, emb, meta = args
        elif len(args) == 4:
            if isinstance(args[2], list):
                d_id, txt, emb, meta = args
                idx = index_name or self.index_name
            else:
                idx, d_id, txt, emb = args
                meta = metadata or {}
        elif len(args) == 3:
            d_id, txt, emb = args
            idx = index_name or self.index_name
            meta = metadata or {}
        else:
            idx = index_name or self.index_name
            d_id = doc_id
            txt = text
            emb = embedding
            meta = metadata or {}

        if d_id is None or txt is None or emb is None:
            raise ValueError("Parameter doc_id, text, dan embedding wajib diisi.")

        if self.backend == "chroma":
            return self._index_document_chroma(idx, d_id, txt, emb, meta)

        body = {
            "text": txt,
            "embedding": emb,
            "metadata": meta or {},
        }

        if self.client is not None:
            try:
                res = self.client.index(
                    index=idx,
                    id=str(d_id),
                    body=body,
                    refresh=True,
                )
                return res
            except Exception as e:
                # Jangan menelan RequestError, ValueError, atau error dari injected/mock client
                if (
                    type(e).__name__ in ("RequestError", "ValueError", "TypeError")
                    or isinstance(e, (ValueError, TypeError))
                    or (self._client is not None and not (HAS_OPENSEARCH_PY and isinstance(self._client, OpenSearch)))
                ):
                    raise
                logger.warning(
                    f"OpenSearch client index_document failed, using HTTP fallback: {e}"
                )

        with httpx.Client(timeout=30.0) as http_client:
            res = http_client.put(
                f"{self.base_url}/{idx}/_doc/{d_id}?refresh=true",
                json=body,
            )
            res.raise_for_status()
            return res.json()

    # -------------------------------------------------------------------------
    # Search & Retrieval
    # -------------------------------------------------------------------------

    def search(
        self,
        *args,
        index_name: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        k: int = 3,
        metadata_filter: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Mencari dokumen terdekat berdasarkan query vector k-NN.
        Mendukung pemanggilan:
        - search(query_embedding, k=3)
        - search(index_name, query_embedding, k=3)
        """
        # Resolusi argumen posisional
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], list):
            idx = args[0]
            q_emb = args[1]
            if len(args) >= 3 and isinstance(args[2], int):
                k = args[2]
        elif len(args) >= 1 and isinstance(args[0], list):
            idx = index_name or self.index_name
            q_emb = args[0]
            if len(args) >= 2 and isinstance(args[1], int):
                k = args[1]
        else:
            idx = index_name or self.index_name
            q_emb = query_embedding

        if q_emb is None:
            raise ValueError("query_embedding wajib diisi.")

        if self.backend == "chroma":
            return self._search_chroma(idx, q_emb, k, metadata_filter)

        knn_clause: Dict[str, Any] = {
            "vector": q_emb,
            "k": k,
        }
        if metadata_filter:
            knn_clause["filter"] = metadata_filter

        query_body = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": knn_clause
                }
            },
        }

        hits = []
        if self.client is not None:
            try:
                res = self.client.search(index=idx, body=query_body)
                hits = res.get("hits", {}).get("hits", [])
            except Exception as e:
                if (
                    type(e).__name__ in ("RequestError", "ValueError", "TypeError")
                    or isinstance(e, (ValueError, TypeError))
                    or (self._client is not None and not (HAS_OPENSEARCH_PY and isinstance(self._client, OpenSearch)))
                ):
                    raise
                logger.warning(
                    f"OpenSearch client search failed, attempting HTTP fallback: {e}"
                )
                hits = self._search_http(idx, query_body)
        else:
            hits = self._search_http(idx, query_body)

        results = []
        for hit in hits:
            source = hit.get("_source", {})
            results.append({
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "text": source.get("text", ""),
                "metadata": source.get("metadata", {}),
            })
        return results

    def _search_http(self, idx: str, query_body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback search via direct HTTP REST."""
        with httpx.Client(timeout=30.0) as http_client:
            res = http_client.post(
                f"{self.base_url}/{idx}/_search",
                json=query_body,
            )
            res.raise_for_status()
            data = res.json()
            return data.get("hits", {}).get("hits", [])

    # -------------------------------------------------------------------------
    # Diagnostics & Utilities
    # -------------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Mengecek status kesehatan OpenSearch cluster."""
        if self.client is not None:
            try:
                return self.client.cluster.health(request_timeout=1.5)
            except Exception:
                pass
        try:
            with httpx.Client(timeout=1.5) as http_client:
                res = http_client.get(f"{self.base_url}/_cluster/health")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
        return {"status": "unreachable"}

    def count(self, index_name: Optional[str] = None) -> int:
        """Menghitung jumlah dokumen dalam index."""
        idx = index_name or self.index_name
        if self.client is not None:
            try:
                res = self.client.count(index=idx)
                return int(res.get("count", 0))
            except Exception:
                pass
        try:
            with httpx.Client(timeout=5.0) as http_client:
                res = http_client.get(f"{self.base_url}/{idx}/_count")
                if res.status_code == 200:
                    return int(res.json().get("count", 0))
        except Exception:
            return 0
        return 0

    # -------------------------------------------------------------------------
    # ChromaDB Fallback / Dual-backend Stubs
    # -------------------------------------------------------------------------

    def _ensure_index_chroma(self, idx: str) -> bool:
        try:
            import chromadb
            host = os.getenv("CHROMA_HOST", "localhost")
            port = int(os.getenv("CHROMA_PORT", 8000))
            client = chromadb.HttpClient(host=host, port=port)
            client.get_or_create_collection(name=idx)
            return True
        except Exception as e:
            logger.warning(f"Chroma fallback ensure_index error: {e}")
            return False

    def _index_document_chroma(
        self, idx: str, doc_id: str, text: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            import chromadb
            host = os.getenv("CHROMA_HOST", "localhost")
            port = int(os.getenv("CHROMA_PORT", 8000))
            client = chromadb.HttpClient(host=host, port=port)
            coll = client.get_or_create_collection(name=idx)
            coll.upsert(ids=[str(doc_id)], documents=[text], embeddings=[embedding], metadatas=[metadata])
            return {"result": "created", "_id": doc_id}
        except Exception as e:
            logger.error(f"Chroma fallback index_document error: {e}")
            raise

    def _search_chroma(
        self, idx: str, query_embedding: List[float], k: int, metadata_filter: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        try:
            import chromadb
            host = os.getenv("CHROMA_HOST", "localhost")
            port = int(os.getenv("CHROMA_PORT", 8000))
            client = chromadb.HttpClient(host=host, port=port)
            coll = client.get_collection(name=idx)
            query_kwargs: Dict[str, Any] = {"query_embeddings": [query_embedding], "n_results": k}
            if metadata_filter:
                query_kwargs["where"] = metadata_filter
            res = coll.query(**query_kwargs)
            results = []
            if res and res.get("ids") and len(res["ids"]) > 0:
                ids = res["ids"][0]
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0] if "distances" in res else [0.0] * len(ids)
                for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
                    score = 1.0 - (dist if dist is not None else 0.0)
                    results.append({"id": doc_id, "score": score, "text": doc, "metadata": meta or {}})
            return results
        except Exception as e:
            logger.error(f"Chroma fallback search error: {e}")
            return []
