#!/usr/bin/env python3
"""
Script Penyusun Kamus Normalisasi Slang & Singkatan (Task D-03).
Menganalisis frekuensi kata tidak baku dan singkatan chat yang BENAR-BENAR MUNCUL
di dataset komentar bersih, lalu menghasilkan:
1. data/slang_dict.json (Kamus mapping JSON)
2. docs/KAMUS_NORMALISASI_SLANG.md (Dokumentasi istilah sebelum -> sesudah)
"""

import csv
import json
import os
import re
from collections import Counter
from datetime import datetime

INPUT_CSV = "data/processed/comments_cleaned.csv"
OUTPUT_JSON = "data/slang_dict.json"
OUTPUT_DOC_MD = "docs/KAMUS_NORMALISASI_SLANG.md"

# Master Slang Candidates (Istilah tidak baku / singkatan lazim di medsos Indonesia)
MASTER_SLANG_CANDIDATES = {
    # Singkatan kata hubung & partikel
    "yg": "yang",
    "dgn": "dengan",
    "dg": "dengan",
    "utk": "untuk",
    "u/": "untuk",
    "u": "untuk",
    "krn": "karena",
    "karna": "karena",
    "tp": "tetapi",
    "tpi": "tetapi",
    "sbg": "sebagai",
    "sdh": "sudah",
    "udh": "sudah",
    "udah": "sudah",
    "dah": "sudah",
    "blm": "belum",
    "lom": "belum",
    "tdk": "tidak",
    "tak": "tidak",
    "gak": "tidak",
    "ga": "tidak",
    "gk": "tidak",
    "nggak": "tidak",
    "ngga": "tidak",
    "bkn": "bukan",
    "klo": "kalau",
    "kalo": "kalau",
    "kl": "kalau",
    "klau": "kalau",
    "jika": "jika",
    "jg": "juga",
    "jga": "juga",
    "dri": "dari",
    "dr": "dari",
    "drpd": "daripada",
    "dlm": "dalam",
    "sampe": "sampai",
    "smp": "sampai",
    "smpe": "sampai",
    "bgt": "banget",
    "bngt": "banget",
    "bgtu": "begitu",
    "gitu": "begitu",
    "gt": "begitu",
    "gini": "begini",
    "gmn": "bagaimana",
    "gmna": "bagaimana",
    "gmana": "bagaimana",
    "knp": "kenapa",
    "knapa": "kenapa",
    "napa": "kenapa",
    "dpt": "dapat",
    "dapet": "dapat",
    "bisa": "bisa",
    "bs": "bisa",
    "bsa": "bisa",
    "tau": "tahu",
    "mw": "mau",
    "pgn": "pengin",
    "pengen": "pengin",

    # Subjek / Panggilan / Kata Ganti
    "sy": "saya",
    "gw": "saya",
    "gue": "saya",
    "gua": "saya",
    "aku": "saya",
    "lu": "kamu",
    "loe": "kamu",
    "elo": "kamu",
    "km": "kamu",
    "kmu": "kamu",
    "org": "orang",
    "org2": "orang-orang",
    "mrk": "mereka",
    "bg": "abang",
    "bang": "abang",
    "bng": "abang",
    "om": "om",
    "pak": "bapak",
    "bpk": "bapak",

    # Waktu & Keterangan
    "skrg": "sekarang",
    "skrng": "sekarang",
    "sblm": "sebelum",
    "sblmnya": "sebelumnya",
    "sesdh": "sesudah",
    "br": "baru",
    "tadi": "tadi",
    "td": "tadi",
    "kemaren": "kemarin",
    "kmrn": "kemarin",
    "slalu": "selalu",
    "sllu": "selalu",
    "sering": "sering",

    # Kosakata Informal / Gadget / Medsos
    "hp": "handphone",
    "hape": "handphone",
    "batere": "baterai",
    "batre": "baterai",
    "camera": "kamera",
    "spek": "spesifikasi",
    "worthit": "sepadan",
    "mantap": "mantap",
    "mantapz": "mantap",
    "mantul": "mantap betul",
    "keren": "keren",
    "parah": "parah",
    "bener": "benar",
    "beneran": "sungguhan",
    "emg": "memang",
    "emang": "memang",
    "cuma": "hanya",
    "cuman": "hanya",
    "aja": "saja",
    "doang": "saja",
    "dlu": "dulu",
    "duluan": "dahulu",
    "smg": "semoga",
    "moga": "semoga",
    "makasih": "terima kasih",
    "trims": "terima kasih",
    "thx": "terima kasih",
    "thanks": "terima kasih",
    "pnting": "penting",
    "pdhl": "padahal",
    "padhal": "padahal",
    "jir": "waduh",
    "jirr": "waduh",
    "anjir": "waduh",
    "anjg": "anjing",
    "wkwk": "tertawa",
    "wkwkwk": "tertawa",
    "wk": "tertawa",
}


def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} tidak ditemukan!")
        return

    # Kumpulkan semua token/kata dari komentar bersih
    words_counter = Counter()
    sample_contexts = {}

    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comment = row.get("comment", "")
            tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", comment.lower())
            for t in tokens:
                words_counter[t] += 1
                if t not in sample_contexts and len(comment) <= 120:
                    sample_contexts[t] = comment

    # Filter: Hanya masukkan ke kamus istilah yang BENAR-BENAR MUNCUL di dataset
    active_slang_dict = {}
    verified_entries = []

    for slang, standard in MASTER_SLANG_CANDIDATES.items():
        freq = words_counter.get(slang.lower(), 0)
        if freq > 0:
            active_slang_dict[slang] = standard
            sample = sample_contexts.get(slang.lower(), "(muncul di komentar panjang)")
            verified_entries.append({
                "slang": slang,
                "standard": standard,
                "frequency": freq,
                "sample": sample,
            })

    # Urutkan berdasarkan frekuensi terbanyak
    verified_entries.sort(key=lambda x: x["frequency"], reverse=True)

    # 1. Simpan File JSON Kamus
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(active_slang_dict, f, ensure_ascii=False, indent=2)

    print(f"Kamus normalisasi tersimpan di {OUTPUT_JSON} (Total istilah aktif: {len(active_slang_dict)})")

    # 2. Simpan Dokumentasi Kamus (docs/KAMUS_NORMALISASI_SLANG.md)
    os.makedirs(os.path.dirname(OUTPUT_DOC_MD), exist_ok=True)
    with open(OUTPUT_DOC_MD, "w", encoding="utf-8") as f:
        f.write("# 📖 Kamus Normalisasi Slang & Singkatan (Task D-03)\n\n")
        f.write(f"**Tanggal Pembaruan:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Basis Data:** `data/processed/comments_cleaned.csv` (1.498 komentar bersih)\n")
        f.write(f"**File Kamus Mesin:** `data/slang_dict.json`\n")
        f.write("**Status Task:** ✅ **SELESAI (DONE)**\n\n")
        f.write("---\n\n")
        f.write("## 1. Ringkasan Kamus\n\n")
        f.write(f"Kamus ini memuat **{len(active_slang_dict)} istilah slang dan singkatan** bahasa Indonesia ")
        f.write("yang **secara empiris terbukti muncul** di dalam dataset media sosial S.O.N.A.R.\n\n")
        f.write("Tujuan utama normalisasi ini adalah menyamakan representasi semantik teks sebelum di-embed ke vektor 768 dimensi ")
        f.write("(Modul 11) sehingga kata informal seperti `yg`, `gak`, `skrg` dipetakan ke makna baku `yang`, `tidak`, `sekarang`.\n\n")
        f.write("---\n\n")
        f.write("## 2. Daftar Istilah (Sebelum ➔ Sesudah) & Frekuensi Kemunculan\n\n")
        f.write("| No | Bentuk Asal (Slang/Singkatan) | Bentuk Baku (Normalisasi) | Frekuensi di Dataset | Contoh Konteks Nyata di Dataset |\n")
        f.write("| :---: | :--- | :--- | :---: | :--- |\n")
        for i, item in enumerate(verified_entries, start=1):
            samp = item["sample"].replace("\n", " ")
            if len(samp) > 70:
                samp = samp[:67] + "..."
            f.write(f"| {i} | `{item['slang']}` | **{item['standard']}** | {item['frequency']:,}x | \"{samp}\" |\n")

        f.write("\n---\n\n")
        f.write("## 3. Kriteria Selesai (Checklist PM)\n\n")
        f.write(f"- [x] Kamus mencakup {len(active_slang_dict)} istilah yang benar-benar muncul di dataset riil.\n")
        f.write("- [x] Format mesin tersedia dalam JSON (`data/slang_dict.json`).\n")
        f.write("- [x] Format dokumentasi manusia tersedia dengan perbandingan Sebelum ➔ Sesudah.\n")
        f.write("- [x] Siap diintegrasikan ke pipeline preprocessing D-04.\n")

    print(f"Dokumentasi kamus berhasil ditulis ke {OUTPUT_DOC_MD}.")


if __name__ == "__main__":
    main()
