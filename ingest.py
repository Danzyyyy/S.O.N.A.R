"""
Root Ingestion Script: Supports OpenSearch (Pertemuan 6 / R3) and ChromaDB.
Indexes both knowledge-base documents (.md, .pdf, .txt) and social media comments (.csv).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Tuple

import pandas as pd

from app.embeddings import embed_text
from app.ingest import extract_text, ingest_knowledge_base
from app.vector_store import VectorStore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Environment Configurations
OPENSEARCH_BASE_URL = os.getenv("OPENSEARCH_BASE_URL", "http://localhost:9200")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = "social_media_sentiments"
OPENSEARCH_DOCS_INDEX = "knowledge-base"
CSV_PATH = os.getenv("CSV_PATH", "data/social_media_comments.csv")
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "knowledge-base")


# =====================================================================
# ChromaDB Backwards-Compatible Utilities
# =====================================================================

def get_embeddings():
    """Menginisialisasi OllamaEmbeddings untuk kompatibilitas Chroma / LangChain."""
    try:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=EMBED_MODEL)
    except Exception as e:
        logger.warning(f"langchain_ollama tidak tersedia: {e}")
        return None


def get_chroma_client():
    """Menginisialisasi HttpClient untuk ChromaDB."""
    try:
        import chromadb
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    except Exception as e:
        logger.warning(f"chromadb client error: {e}")
        return None


def get_vector_store():
    """Mendapatkan instance Chroma vector store untuk Streamlit / skrip legacy."""
    from langchain_chroma import Chroma
    client = get_chroma_client()
    embeddings = get_embeddings()
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )


def load_documents_from_csv(csv_path: str = CSV_PATH) -> Tuple[List[Any], List[str]]:
    """Membaca CSV dan mengonversi ke list Document LangChain."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File dataset tidak ditemukan di: {csv_path}")

    from langchain_core.documents import Document

    df = pd.read_csv(csv_path)
    documents = []
    ids = []

    for _, row in df.iterrows():
        doc_id = str(row["id"])
        content = str(row["comment"])
        metadata = {
            "id": int(row["id"]),
            "timestamp": str(row["timestamp"]),
            "platform": str(row["platform"]),
            "username": str(row["username"]),
            "sentiment": str(row["sentiment"]),
            "topic": str(row["topic"]),
            "likes": int(row["likes"]),
        }
        documents.append(Document(page_content=content, metadata=metadata))
        ids.append(doc_id)

    return documents, ids


def ingest_data(csv_path: str = CSV_PATH) -> int:
    """Melakukan proses indexing data komentar CSV ke ChromaDB (legacy)."""
    logger.info(f"[Chroma Ingest] Menghubungkan ke ChromaDB di {CHROMA_HOST}:{CHROMA_PORT}...")
    from langchain_chroma import Chroma

    client = get_chroma_client()
    collections = client.list_collections()
    collection_names = [c.name for c in collections]
    if COLLECTION_NAME in collection_names:
        logger.info(f"[Chroma Ingest] Mereset collection '{COLLECTION_NAME}'...")
        client.delete_collection(name=COLLECTION_NAME)

    documents, ids = load_documents_from_csv(csv_path)
    embeddings = get_embeddings()
    vs = Chroma(client=client, collection_name=COLLECTION_NAME, embedding_function=embeddings)
    vs.add_documents(documents=documents, ids=ids)
    logger.info(f"[Chroma Ingest] Sukses indexing {len(documents)} dokumen.")
    return len(documents)


# =====================================================================
# OpenSearch Ingestion Pipeline
# =====================================================================

def ingest_csv_to_opensearch(
    csv_path: str = CSV_PATH,
    index_name: str = "social-media-sentiments",
    base_url: str = OPENSEARCH_BASE_URL,
    ollama_url: str = OLLAMA_BASE_URL,
) -> int:
    """
    Mengindeks seluruh data komentar CSV ke dalam OpenSearch k-NN vector index.
    """
    if not os.path.exists(csv_path):
        logger.warning(f"File CSV tidak ditemukan di: {csv_path}")
        return 0

    df = pd.read_csv(csv_path)
    vs = VectorStore(base_url=base_url, index_name=index_name)
    logger.info(f"[OpenSearch] Memastikan index '{index_name}' siap...")
    vs.ensure_index(index_name=index_name)

    ingested = 0
    for _, row in df.iterrows():
        doc_id = f"comment-{row['id']}"
        comment_text = str(row["comment"])
        metadata = {
            "id": int(row["id"]),
            "timestamp": str(row["timestamp"]),
            "platform": str(row["platform"]),
            "username": str(row["username"]),
            "sentiment": str(row["sentiment"]),
            "topic": str(row["topic"]),
            "likes": int(row["likes"]),
        }

        try:
            emb = embed_text(comment_text, base_url=ollama_url, model=EMBED_MODEL)
            vs.index_document(
                index_name=index_name,
                doc_id=doc_id,
                text=comment_text,
                embedding=emb,
                metadata=metadata,
            )
            ingested += 1
        except Exception as e:
            logger.error(f"[OpenSearch] Gagal mengindeks comment id {row['id']}: {e}")

    logger.info(f"[OpenSearch] Sukses mengindeks {ingested} komentar ke index '{index_name}'.")
    return ingested


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base and CSV into vector store.")
    parser.add_argument(
        "--target",
        choices=["opensearch", "chroma", "all"],
        default="opensearch",
        help="Target vector database (default: opensearch)",
    )
    parser.add_argument(
        "--kb-dir",
        default=KNOWLEDGE_BASE_PATH,
        help="Direktori knowledge base SOPs",
    )
    parser.add_argument(
        "--csv-file",
        default=CSV_PATH,
        help="File path CSV dataset",
    )
    args = parser.parse_args()

    total_kb = 0
    total_csv = 0

    if args.target in ("opensearch", "all"):
        logger.info("=== Menjalankan Ingestion OpenSearch ===")
        try:
            total_kb = ingest_knowledge_base(
                kb_path=args.kb_dir,
                base_url=OPENSEARCH_BASE_URL,
                embed_model=EMBED_MODEL,
                index_name=OPENSEARCH_DOCS_INDEX,
            )
        except Exception as e:
            logger.error(f"Error ingestion knowledge base ke OpenSearch: {e}")

        try:
            total_csv = ingest_csv_to_opensearch(
                csv_path=args.csv_file,
                index_name="social-media-sentiments",
                base_url=OPENSEARCH_BASE_URL,
                ollama_url=OLLAMA_BASE_URL,
            )
        except Exception as e:
            logger.error(f"Error ingestion CSV ke OpenSearch: {e}")

    if args.target in ("chroma", "all"):
        logger.info("=== Menjalankan Ingestion ChromaDB ===")
        try:
            ingest_data(args.csv_file)
        except Exception as e:
            logger.error(f"Error ingestion CSV ke Chroma: {e}")

    print(f"\n[Ingest Summary] Target: {args.target}")
    print(f"  Knowledge base documents: {total_kb}")
    print(f"  Social media comments:    {total_csv}")


if __name__ == "__main__":
    main()
