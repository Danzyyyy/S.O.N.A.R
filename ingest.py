import os
import sys
import pandas as pd
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = "social_media_sentiments"
CSV_PATH = os.getenv("CSV_PATH", "data/social_media_comments.csv")


def get_embeddings():
    """Menginisialisasi OllamaEmbeddings."""
    return OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model=EMBED_MODEL
    )


def get_chroma_client():
    """Menginisialisasi HttpClient untuk ChromaDB."""
    return chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT
    )


def get_vector_store():
    """Mendapatkan instance Chroma vector store."""
    client = get_chroma_client()
    embeddings = get_embeddings()
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )


def load_documents_from_csv(csv_path: str = CSV_PATH):
    """Membaca CSV dan mengonversi ke list Document LangChain."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File dataset tidak ditemukan di: {csv_path}")

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
            "likes": int(row["likes"])
        }
        documents.append(Document(page_content=content, metadata=metadata))
        ids.append(doc_id)

    return documents, ids


def ingest_data(csv_path: str = CSV_PATH) -> int:
    """Melakukan proses indexing data komentar CSV ke ChromaDB."""
    print(f"[Ingest] Menghubungkan ke ChromaDB di {CHROMA_HOST}:{CHROMA_PORT}...")
    client = get_chroma_client()

    # Hapus collection lama jika sudah ada untuk reset bersih
    collections = client.list_collections()
    collection_names = [c.name for c in collections]
    if COLLECTION_NAME in collection_names:
        print(f"[Ingest] Mereset collection '{COLLECTION_NAME}'...")
        client.delete_collection(name=COLLECTION_NAME)

    print(f"[Ingest] Membaca dataset dari {csv_path}...")
    documents, ids = load_documents_from_csv(csv_path)

    print(f"[Ingest] Menginisialisasi embeddings ({EMBED_MODEL}) via {OLLAMA_BASE_URL}...")
    embeddings = get_embeddings()

    print(f"[Ingest] Menyimpan {len(documents)} dokumen ke ChromaDB...")
    vector_store = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )

    vector_store.add_documents(documents=documents, ids=ids)
    print(f"[Ingest] Sukses melakukan indexing {len(documents)} dokumen!")
    return len(documents)


if __name__ == "__main__":
    try:
        total = ingest_data()
        print(f"Selesai! Total dokumen terindeks: {total}")
    except Exception as e:
        print(f"Error saat ingest data: {e}", file=sys.stderr)
        sys.exit(1)
