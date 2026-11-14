"""Fase 2a ΓÇö Query Router untuk S.O.N.A.R (TERPASANG 14 Nov 2026).

Sumber spesifikasi: ``prompt_agentic_rag_s_o_n_a_r.md`` bagian 1
(Query Router & Decomposition Agent) dan perencanaan-lanjutan-sonar.docx
Fase 2a: "Router dulu, tanpa mengubah jawaban."

Perilaku yang direncanakan:
- VECTORSTORE -> jalankan alur retrieval yang sekarang (SOP + komentar).
- DIRECT_CHAT -> jawab tanpa retrieval (salam, basa-basi, klarifikasi umum).
- WEB_SEARCH -> belum diaktifkan (belum ada sumber web yang disepakati);
  dicatat di log sebagai rute belum didukung, lalu diperlakukan sebagai
  VECTORSTORE supaya chat tidak gagal ΓÇö BUKAN pura-pura browsing.
- Kalau Ollama tidak bisa dihubungi atau JSON-nya tidak valid, pakai
  fallback berbasis kata kunci (di bawah) dan log alasannya, lalu
  default ke VECTORSTORE. Chat tidak boleh gagal hanya karena router.

Catatan latensi: router memakai satu panggilan LLM pendek
(num_predict 256, temperature 0) SEBELUM retrieval/streaming dimulai,
sesuai rencana "tahap router dan grader berjalan sebelum streaming".
Di CPU (~45 tok/detik) itu menambah belasan detik ΓÇö wajar untuk Sesi 3,
dan alasan kenapa keluaran router dibatasi JSON pendek.
"""

import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)

ROUTES = ("VECTORSTORE", "DIRECT_CHAT", "WEB_SEARCH")
TOPICS = (
    "QRIS_TRANSACTION",
    "APP_UPDATE",
    "CUSTOMER_SERVICE",
    "GENERAL_SENTIMENT",
    "OTHER",
)

ROUTER_SYSTEM_PROMPT = """Anda adalah Router Agent cerdas untuk sistem analitik media sosial S.O.N.A.R.
Tugas Anda adalah menganalisis pesan pengguna dan mengklasifikasikan rute eksekusi data.

Kategori Rute:
1. "VECTORSTORE": Pertanyaan membutuhkan pencarian data internal media sosial (tweet pengguna, komplain nasabah/netizen, ulasan app store, sentimen historis QRIS, komplain CS, update v2.4).
2. "DIRECT_CHAT": Percakapan santai, salam pembuka, klarifikasi umum, atau pertanyaan dasar tanpa perlu data retrieval.
3. "WEB_SEARCH": Pertanyaan mengenai tren eksternal terbaru, berita nasional/global terkini di luar data internal.

Keluarkan output HANYA dalam format JSON valid tanpa komentar tambahan:
{
  "route": "VECTORSTORE" | "DIRECT_CHAT" | "WEB_SEARCH",
  "topic": "QRIS_TRANSACTION" | "APP_UPDATE" | "CUSTOMER_SERVICE" | "GENERAL_SENTIMENT" | "OTHER",
  "search_queries": ["daftar kueri pencarian semantik yang dioptimalkan untuk ChromaDB"],
  "requires_sentiment_analysis": true | false
}"""

# Fallback kata kunci ΓÇö hanya dipakai kalau LLM gagal. Sengaja sempit:
# salam / terima kasih / perpisahan -> DIRECT_CHAT, sisanya VECTORSTORE.
_GREETINGS = (
    "halo", "hai", "hi", "selamat pagi", "selamat siang", "selamat sore",
    "selamat malam", "terima kasih", "makasih", "thanks", "dadah", "bye",
    "apa kabar",
)
_TOPIC_KEYWORDS = (
    ("QRIS_TRANSACTION", ("qris", "saldo terpotong", "double debit", "timeout", "transaksi gagal")),
    ("APP_UPDATE", ("v2.4", "update aplikasi", "force close", "lag", "crash", "aplikasi")),
    ("CUSTOMER_SERVICE", ("customer service", "cs", "respon lambat", "tiket", "komplain")),
    ("GENERAL_SENTIMENT", ("sentimen", "netizen", "keluhan", "ulasan", "opini publik")),
)


def _fallback_route(query: str) -> dict:
    """Klasifikasi darurat tanpa LLM. Tidak pernah melempar exception."""
    q = (query or "").strip().lower()
    if not q:
        return {"route": "DIRECT_CHAT", "topic": "OTHER",
                "search_queries": [], "requires_sentiment_analysis": False,
                "fallback": True, "fallback_reason": "query kosong"}
    if any(g in q for g in _GREETINGS) and len(q) <= 40:
        return {"route": "DIRECT_CHAT", "topic": "OTHER",
                "search_queries": [], "requires_sentiment_analysis": False,
                "fallback": True, "fallback_reason": "salam/basa-basi"}
    for topic, keywords in _TOPIC_KEYWORDS:
        if any(k in q for k in keywords):
            return {"route": "VECTORSTORE", "topic": topic,
                    "search_queries": [query.strip()],
                    "requires_sentiment_analysis": topic != "OTHER",
                    "fallback": True, "fallback_reason": "kata kunci topik"}
    return {"route": "VECTORSTORE", "topic": "OTHER",
            "search_queries": [query.strip()],
            "requires_sentiment_analysis": False,
            "fallback": True, "fallback_reason": "default aman"}


def _parse_router_json(raw: str) -> dict | None:
    """Ambil objek JSON pertama dari jawaban LLM; None kalau tidak ada."""
    if not raw:
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("route") not in ROUTES:
        return None
    topic = data.get("topic") if data.get("topic") in TOPICS else "OTHER"
    queries = data.get("search_queries") or []
    if not isinstance(queries, list):
        queries = []
    return {
        "route": data["route"],
        "topic": topic,
        "search_queries": [str(x) for x in queries][:5],
        "requires_sentiment_analysis": bool(data.get("requires_sentiment_analysis", False)),
        "fallback": False,
    }


def route_query(query: str, ollama_base_url: str = "http://localhost:11434",
                model: str = "llama3.2:3b", timeout: float = 120.0) -> dict:
    """Klasifikasikan satu pertanyaan pengguna. Selalu mengembalikan dict.

    Mengembalikan dict route/topic/search_queries/requires_sentiment_analysis
    plus "fallback" (bool) dan, bila fallback, "fallback_reason".
    """
    if not query or not query.strip():
        return _fallback_route(query)
    try:
        with httpx.Client(timeout=timeout) as client:
            res = client.post(
                f"{ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                        {"role": "user", "content": query.strip()},
                    ],
                    "stream": False,
                    "options": {"temperature": 0, "num_predict": 256},
                },
            )
            res.raise_for_status()
            raw = res.json().get("message", {}).get("content", "")
    except Exception as exc:  # Ollama mati / timeout: jangan matikan chat
        logger.warning("Router LLM gagal (%s); pakai fallback kata kunci", exc)
        return _fallback_route(query)
    parsed = _parse_router_json(raw)
    if parsed is None:
        logger.warning("Router LLM mengembalikan JSON tidak valid; pakai fallback")
        return _fallback_route(query)
    if parsed["route"] == "WEB_SEARCH":
        logger.info("Router: WEB_SEARCH belum didukung, diperlakukan sebagai VECTORSTORE")
    logger.info("Router: route=%s topic=%s queries=%s",
                parsed["route"], parsed["topic"], parsed["search_queries"])
    return parsed


if __name__ == "__main__":
    # Uji cepat fallback tanpa Ollama: `python -m app.router`
    cases = [
        "halo",
        "Apa akar penyebab lonjakan keluhan transaksi QRIS yang timeout?",
        "Bagaimana sentimen netizen soal update aplikasi v2.4?",
        "Kenapa respon customer service lambat?",
        "terima kasih",
        "Berita terbaru tentang suku bunga hari ini?",
    ]
    for case in cases:
        print(case, "->", _fallback_route(case))
