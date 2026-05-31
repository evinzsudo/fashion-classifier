#!/usr/bin/env python3
"""
Download 50 diverse fashion garment images from the Pexels API
into eval/test_images/.

Requires PEXELS_API_KEY in the project .env file (or environment).
Sign up free at https://www.pexels.com/api/

Usage:
    python eval/download_test_images.py
    python eval/download_test_images.py --count 50 --per-term 5
"""

import argparse
import re
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent / ".env")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# 10 terms × 5 images = 50 images
SEARCH_TERMS = [
    "dress",
    "jacket",
    "sweater",
    "jeans",
    "suit",
    "coat",
    "blouse",
    "skirt",
    "sneakers",
    "handbag",
]

OUTPUT_DIR = Path(__file__).parent / "test_images"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def fetch_photos(term: str, per_page: int, page: int = 1) -> list[dict]:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": f"{term} fashion clothing",
        "per_page": per_page,
        "page": page,
        "orientation": "portrait",
    }
    response = httpx.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("photos", [])


def download_photo(photo: dict, dest: Path) -> bool:
    # Use 'large' (max 1280px wide) — good resolution without huge file sizes
    url = photo["src"].get("large") or photo["src"].get("original")
    if not url:
        return False
    response = httpx.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return True


def main(per_term: int = 5) -> None:
    if not PEXELS_API_KEY:
        print(
            "ERROR: PEXELS_API_KEY is not set.\n"
            "Add it to your .env file:\n"
            "  PEXELS_API_KEY=your_key_here\n"
            "Get a free key at https://www.pexels.com/api/",
            file=sys.stderr,
        )
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    seen_ids: set[int] = set()
    total_downloaded = 0
    total_skipped = 0

    print(f"Downloading {per_term} images × {len(SEARCH_TERMS)} terms "
          f"= {per_term * len(SEARCH_TERMS)} images\n"
          f"Output: {OUTPUT_DIR}\n")

    for term in SEARCH_TERMS:
        term_downloaded = 0
        page = 1

        print(f"  [{term}]", end=" ", flush=True)

        while term_downloaded < per_term:
            needed = per_term - term_downloaded
            try:
                photos = fetch_photos(term, per_page=min(needed + 2, 10), page=page)
            except httpx.HTTPStatusError as e:
                print(f"\n  HTTP error fetching '{term}': {e.response.status_code}")
                break
            except Exception as e:
                print(f"\n  Error fetching '{term}': {e}")
                break

            if not photos:
                print(f"(no more results at page {page})")
                break

            for photo in photos:
                if term_downloaded >= per_term:
                    break

                photo_id = photo["id"]
                if photo_id in seen_ids:
                    total_skipped += 1
                    continue
                seen_ids.add(photo_id)

                # Descriptive filename: {term}_{index:03d}_pexels_{id}.jpg
                index = total_downloaded + 1
                filename = f"{slugify(term)}_{index:03d}_pexels_{photo_id}.jpg"
                dest = OUTPUT_DIR / filename

                if dest.exists():
                    print(".", end="", flush=True)
                    term_downloaded += 1
                    total_downloaded += 1
                    continue

                try:
                    download_photo(photo, dest)
                    print(".", end="", flush=True)
                    term_downloaded += 1
                    total_downloaded += 1
                    # Respect Pexels rate limit (200 req/hour free tier)
                    time.sleep(0.4)
                except Exception as e:
                    print(f"x", end="", flush=True)
                    dest.unlink(missing_ok=True)

            page += 1
            if page > 5:
                break  # give up after 5 pages

        print(f"  ({term_downloaded} saved)")

    print(f"\nDone. {total_downloaded} images downloaded to {OUTPUT_DIR}/")
    if total_skipped:
        print(f"       {total_skipped} duplicate photo IDs skipped.")

    # Remind user to fill in labels
    labels_path = Path(__file__).parent / "labels.json"
    if labels_path.exists():
        import json
        labels = json.loads(labels_path.read_text())
        unlabelled = [
            f.name for f in OUTPUT_DIR.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            and f.name not in labels
            and not f.name.startswith("example_")
        ]
        if unlabelled:
            print(f"\n{len(unlabelled)} images have no labels yet.")
            print("Add entries to eval/labels.json, then run:")
            print("  python eval/evaluate.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Pexels fashion images for evaluation.")
    parser.add_argument(
        "--per-term",
        type=int,
        default=5,
        help="Images to download per search term (default: 5, total = terms × this)",
    )
    args = parser.parse_args()

    if args.per_term < 1 or args.per_term > 80:
        print("--per-term must be between 1 and 80", file=sys.stderr)
        sys.exit(1)

    main(per_term=args.per_term)
