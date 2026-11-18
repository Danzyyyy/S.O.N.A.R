#!/usr/bin/env python3
"""
YouTube Comments Scraper for S.O.N.A.R Data Pipeline (Task D-01).
Mengambil komentar dari satu atau beberapa video YouTube via YouTube Data API v3
dan menyimpannya ke format CSV yang kompatibel dengan skema S.O.N.A.R.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("youtube_scraper")

# Load environment variables dari .env
load_dotenv()


def extract_video_id(url_or_id: str) -> str:
    """Mengekstrak 11-karakter video ID dari berbagai format URL YouTube atau string ID."""
    url_or_id = url_or_id.strip()
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    if len(url_or_id) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", url_or_id):
        return url_or_id
    raise ValueError(f"Tidak dapat mengenali YouTube Video ID dari input: {url_or_id}")


def get_video_title(youtube, video_id: str) -> str:
    """Mendapatkan judul video untuk konteks logging/metadata."""
    try:
        response = youtube.videos().list(part="snippet", id=video_id).execute()
        items = response.get("items", [])
        if items:
            return items[0]["snippet"].get("title", video_id)
    except Exception as e:
        logger.warning(f"Gagal mengambil judul video {video_id}: {e}")
    return video_id


def fetch_comments_for_video(
    youtube,
    video_id: str,
    max_comments: int = 100,
    topic: str = "general",
) -> List[Dict[str, Any]]:
    """Mengambil komentar tingkat atas (top-level comments) dari video tertentu."""
    comments_data: List[Dict[str, Any]] = []
    video_title = get_video_title(youtube, video_id)
    logger.info(f"Mengambil komentar dari: '{video_title}' (ID: {video_id})...")

    next_page_token: Optional[str] = None
    fetched = 0

    while fetched < max_comments:
        batch_size = min(100, max_comments - fetched)
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=batch_size,
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance",
            )
            response = request.execute()
        except HttpError as e:
            if "commentsDisabled" in str(e):
                logger.warning(f"Komentar dinonaktifkan pada video {video_id}.")
            else:
                logger.error(f"Error saat mengambil komentar video {video_id}: {e}")
            break
        except Exception as e:
            logger.error(f"Terjadi kesalahan tak terduga: {e}")
            break

        items = response.get("items", [])
        if not items:
            break

        for item in items:
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            raw_text = snippet.get("textDisplay", "").strip()
            if not raw_text:
                continue

            # Bersihkan newline ganda/berlebihan untuk kenyamanan CSV
            cleaned_text = " ".join(raw_text.split())

            published_at = snippet.get("publishedAt", "")
            timestamp = ""
            if published_at:
                try:
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d")
                except Exception:
                    timestamp = published_at[:10]

            author_name = snippet.get("authorDisplayName", "@anonymous")
            if not author_name.startswith("@"):
                author_name = f"@{author_name.replace(' ', '_').lower()}"

            likes = snippet.get("likeCount", 0)

            comments_data.append({
                "timestamp": timestamp,
                "platform": "YouTube",
                "username": author_name,
                "comment": cleaned_text,
                "sentiment": "neutral",  # placeholder sebelum tahap labeling/klasifikasi D-02
                "topic": topic,
                "likes": int(likes),
                "video_id": video_id,
            })
            fetched += 1
            if fetched >= max_comments:
                break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    logger.info(f"Berhasil menarik {len(comments_data)} komentar dari video {video_id}.")
    return comments_data


def save_to_csv(data: List[Dict[str, Any]], output_path: str, start_id: int = 1):
    """Menyimpan hasil scraping ke file CSV dengan skema S.O.N.A.R."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    fieldnames = ["id", "timestamp", "platform", "username", "comment", "sentiment", "topic", "likes"]
    file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0

    mode = "a" if file_exists else "w"
    
    # Jika mode append dan file sudah ada, tentukan id terakhir
    current_id = start_id
    if file_exists:
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    current_id = int(rows[-1]["id"]) + 1
        except Exception:
            current_id = start_id

    with open(output_path, mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()

        for item in data:
            row = {
                "id": current_id,
                "timestamp": item.get("timestamp", ""),
                "platform": item.get("platform", "YouTube"),
                "username": item.get("username", "@anonymous"),
                "comment": item.get("comment", ""),
                "sentiment": item.get("sentiment", "neutral"),
                "topic": item.get("topic", "general"),
                "likes": item.get("likes", 0),
            }
            writer.writerow(row)
            current_id += 1

    logger.info(f"Data tersimpan di {output_path} (Total baru ditambahkan: {len(data)} baris, ID terakhir: {current_id - 1})")


def search_videos(youtube, query: str, max_videos: int = 3) -> List[str]:
    """Mencari video ID relevan di YouTube berdasarkan query pencarian."""
    logger.info(f"Mencari {max_videos} video relevan untuk query: '{query}'...")
    video_ids = []
    try:
        response = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=max_videos,
            type="video",
        ).execute()
        for item in response.get("items", []):
            vid = item["id"].get("videoId")
            title = item["snippet"].get("title", "")
            if vid:
                video_ids.append(vid)
                logger.info(f"  -> Ditemukan: [{vid}] {title}")
    except Exception as e:
        logger.error(f"Gagal melakukan pencarian video: {e}")
    return video_ids


def main():
    parser = argparse.ArgumentParser(description="Scrape YouTube Comments for S.O.N.A.R Data Pipeline")
    parser.add_argument(
        "-v", "--video",
        action="append",
        default=[],
        help="URL video YouTube atau Video ID (bisa ditentukan berulang kali: -v URL1 -v URL2)",
    )
    parser.add_argument(
        "-s", "--search",
        type=str,
        default=None,
        help="Query pencarian YouTube otomatis (misal: 'qris gagal saldo terpotong')",
    )
    parser.add_argument(
        "--search-videos",
        type=int,
        default=3,
        help="Jumlah video teratas yang diambil saat memakai mode --search (default: 3)",
    )
    parser.add_argument(
        "-m", "--max",
        type=int,
        default=100,
        help="Maksimal jumlah komentar per video (default: 100)",
    )
    parser.add_argument(
        "-t", "--topic",
        type=str,
        default="general",
        help="Label topik default untuk komentar video ini (misal: payment_issue, app_review, feature_praise)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="data/raw/youtube_comments_raw.csv",
        help="Path file CSV output (default: data/raw/youtube_comments_raw.csv)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="YouTube Data API Key (default: membaca dari .env YOUTUBE_API_KEY)",
    )

    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        logger.error("API Key YouTube tidak ditemukan! Simpan di .env (YOUTUBE_API_KEY) atau via argumen --api-key.")
        return

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        logger.error(f"Gagal menginisialisasi YouTube API Client: {e}")
        return

    target_videos = list(args.video)

    if args.search:
        searched_vids = search_videos(youtube, args.search, max_videos=args.search_videos)
        target_videos.extend(searched_vids)

    if not target_videos:
        logger.error("Silakan tentukan minimal satu video dengan -v/--video atau kata kunci pencarian dengan -s/--search.")
        return

    all_comments = []
    for raw_input in target_videos:
        try:
            video_id = extract_video_id(raw_input)
            comments = fetch_comments_for_video(youtube, video_id, max_comments=args.max, topic=args.topic)
            all_comments.extend(comments)
        except Exception as e:
            logger.error(f"Gagal memproses video '{raw_input}': {e}")

    if all_comments:
        save_to_csv(all_comments, args.output)
        print(f"\n Selesai! Sebanyak {len(all_comments)} komentar berhasil disimpan ke '{args.output}'.")
    else:
        print("\n⚠️ Tidak ada komentar yang berhasil diambil.")


if __name__ == "__main__":
    main()
