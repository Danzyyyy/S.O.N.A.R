"""
Ingestion module for knowledge-base documents (PDF, MD, TXT).
Complies with Pertemuan 6 (Modules 10 and 12).
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from pypdf import PdfReader

from app.embeddings import embed_text
from app.vector_store import VectorStore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def extract_text(file_path: str) -> str:
    """
    Ekstraksi teks mentah dari file PDF, Markdown, atau teks biasa.
    Untuk PDF, mengiterasi reader.pages dan menggabungkan teks.
    """
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def ingest_knowledge_base(
    kb_path: Optional[str] = None,
    vector_store: Optional[VectorStore] = None,
    base_url: Optional[str] = None,
    embed_model: str = "nomic-embed-text",
    index_name: str = "knowledge-base",
) -> int:
    """
    Membaca dokumen dari folder knowledge-base, membuat embedding vektor 768 dimensi via Ollama,
    dan mengindeksnya ke dalam OpenSearch.
    """
    target_dir = kb_path or os.getenv("KNOWLEDGE_BASE_PATH", "./knowledge-base")
    ollama_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    if not os.path.exists(target_dir):
        logger.warning(f"Direktori knowledge base tidak ditemukan: {target_dir}")
        return 0

    vs = vector_store or VectorStore(index_name=index_name)
    logger.info(f"Memastikan index '{index_name}' siap pada vector store...")
    vs.ensure_index(index_name=index_name)

    valid_extensions = (".md", ".txt", ".pdf")
    ingested_count = 0

    for root, _, files in os.walk(target_dir):
        for filename in sorted(files):
            if not filename.lower().endswith(valid_extensions):
                continue

            file_path = os.path.join(root, filename)
            doc_id = os.path.splitext(filename)[0]

            try:
                logger.info(f"Mengekstrak teks dari: {filename}")
                content = extract_text(file_path).strip()
                if not content:
                    logger.warning(f"File {filename} kosong, dilewati.")
                    continue

                logger.info(f"Membuat embedding via Ollama ({embed_model})...")
                embedding = embed_text(content, base_url=ollama_url, model=embed_model)

                metadata = {
                    "source": filename,
                    "path": file_path,
                    "extension": os.path.splitext(filename)[1],
                    "length": len(content),
                }

                logger.info(f"Mengindeks dokumen '{doc_id}' ke OpenSearch...")
                vs.index_document(
                    index_name=index_name,
                    doc_id=doc_id,
                    text=content,
                    embedding=embedding,
                    metadata=metadata,
                )
                ingested_count += 1
                logger.info(f"Berhasil mengindeks {filename} (id={doc_id})")

            except Exception as e:
                logger.error(f"Gagal memproses {filename}: {e}")

    logger.info(f"Selesai! Total dokumen diindeks: {ingested_count}")
    return ingested_count


if __name__ == "__main__":
    kb_dir = sys.argv[1] if len(sys.argv) > 1 else None
    count = ingest_knowledge_base(kb_path=kb_dir)
    print(f"Total knowledge base documents ingested: {count}")
