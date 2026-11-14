"""
Chunking SOP per bagian (heading) ΓÇö S.O.N.A.R Fase 1, Langkah 2-4 (DRAF).

Status: TERPASANG 14 Nov 2026 ΓÇö dipakai app/ingest.py saat ingest KB (26 chunk, 3 SOP).
Jangan jalankan re-ingest dari salinan lokal sebelum gerbang di
~/workspace/pds/chunking-fase1-langkah-2-4.md terpenuhi (khususnya:
hapus dulu 3 dokumen utuh lama dari index ΓÇö kalau tidak, dokumen utuh
dan chunk-nya akan sama-sama muncul di hasil retrieval).

Koreksi 2026-11-14: KB kini hanya 3 SOP (KRS + cuti dihapus 13 Nov
malam). Total chunk yang diharapkan 26, bukan 36-37.

Keputusan desain (Langkah 2 ΓÇö overlap):
- Chunk mengikuti heading ## / ###, bukan potong per N karakter, supaya
  satu langkah prosedur tidak terpotong di tengah.
- TIDAK ada overlap karakter antar chunk. Sebagai gantinya, tiap chunk
  diberi header konteks sebelum di-embedding:
  "SOP: <judul SOP> | Bagian: <nama bagian>"
  jadi chunk tetap bisa berdiri sendiri saat di-retrieve.
- Heading induk yang isinya kosong (mis. "6. Prosedur Rinci Pelaksanaan"
  dan "8. Lampiran") dilewati ΓÇö isinya ada di sub-bagiannya.
- Pengaman: kalau ada bagian > 2000 karakter, bagian itu dibelah per
  paragraf dengan overlap 200 karakter. Tidak ada bagian SOP saat ini
  yang memicunya (terbesar 1.716 karakter), jadi pengaman ini belum
  teruji oleh data nyata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_SECTION_CHARS = 2000
LONG_SECTION_TARGET_CHARS = 1800
LONG_SECTION_OVERLAP_CHARS = 200

_HEADING_RE = re.compile(r"^(#{2,3})\s+(.*\S)\s*$")


@dataclass
class Chunk:
    chunk_id: str
    sop: str
    section: str
    parent_section: str | None
    chunk_index: int
    chunk_count: int
    text: str  # sudah termasuk header konteks, siap di-embedding
    length: int  # panjang body tanpa header


def _split_long_section(body: str) -> list[str]:
    """Belah bagian panjang per paragraf, overlap 200 karakter.

    Hanya dipakai kalau satu bagian > MAX_SECTION_CHARS.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    parts: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > LONG_SECTION_TARGET_CHARS:
            parts.append(current)
            # Overlap: bawa ekor 200 karakter terakhir ke potongan berikut.
            current = current[-LONG_SECTION_OVERLAP_CHARS:] + "\n\n" + para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        parts.append(current)
    return parts


def split_markdown_sections(text: str, source: str) -> list[Chunk]:
    """Pecah satu SOP markdown menjadi chunk per bagian.

    source: nama file, mis. "sop-penanganan-insiden-qris.md".
    """
    sop_slug = source.rsplit(".", 1)[0]
    lines = text.splitlines()

    doc_title = ""
    # (level, heading, parent_heading, body_lines)
    sections: list[tuple[int, str, str | None, list[str]]] = []
    current_parent: str | None = None

    for line in lines:
        m = _HEADING_RE.match(line)
        if not m:
            if sections:
                sections[-1][3].append(line)
            continue
        level = len(m.group(1))
        heading = m.group(2).strip()
        if level == 2 and not doc_title and not sections:
            # Heading ## pertama adalah judul SOP, bukan bagian.
            doc_title = heading
            continue
        if level == 2:
            current_parent = heading
            sections.append((level, heading, None, []))
        else:  # level 3
            sections.append((level, heading, current_parent, []))

    # Buang heading induk yang kosong; isinya ada di sub-bagiannya.
    kept = [(lvl, h, p, b) for (lvl, h, p, b) in sections if "".join(b).strip()]

    chunks: list[Chunk] = []
    for _lvl, heading, parent, body_lines in kept:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        bodies = [body] if len(body) <= MAX_SECTION_CHARS else _split_long_section(body)
        for part in bodies:
            header = f"SOP: {doc_title or sop_slug} | Bagian: {heading}"
            full_text = f"{header}\n\n{part}"
            chunks.append(
                Chunk(
                    chunk_id="",  # diisi setelah jumlah total diketahui
                    sop=sop_slug,
                    section=heading,
                    parent_section=parent,
                    chunk_index=0,  # diisi di bawah
                    chunk_count=0,  # diisi di bawah
                    text=full_text,
                    length=len(part),
                )
            )

    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i
        chunk.chunk_count = len(chunks)
        chunk.chunk_id = f"{sop_slug}--{i + 1:02d}"
    return chunks


def chunk_to_metadata(chunk: Chunk, source: str, file_path: str) -> dict:
    """Metadata yang ditulis ke OpenSearch bersama tiap chunk."""
    return {
        "source": source,
        "path": file_path,
        "sop": chunk.sop,
        "section": chunk.section,
        "parent_section": chunk.parent_section,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "chunk_count": chunk.chunk_count,
        "length": chunk.length,
    }
