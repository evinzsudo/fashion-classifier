#!/usr/bin/env python3
"""
Evaluation script for the fashion classifier.

Usage:
    python evaluate.py --api-url http://localhost:8000 \
                       --images-dir ./test_images \
                       --labels ./labels.json

labels.json format:
{
  "shirt_001.jpg": {
    "garment_type": "shirt",
    "style": "casual",
    "material": "cotton",
    "color_palette": "solid white",
    "pattern": "solid",
    "season": "all-season",
    "occasion": "casual everyday",
    "consumer_profile": "young professional",
    "location_context": "urban"
  },
  ...
}
"""

import argparse
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

import httpx

ATTRIBUTES = [
    "garment_type",
    "style",
    "material",
    "color_palette",
    "pattern",
    "season",
    "occasion",
    "consumer_profile",
    "location_context",
]


def upload_image(api_url: str, image_path: Path) -> dict:
    with open(image_path, "rb") as f:
        mime = "image/jpeg"
        suffix = image_path.suffix.lower()
        if suffix == ".png":
            mime = "image/png"
        elif suffix == ".webp":
            mime = "image/webp"
        elif suffix == ".gif":
            mime = "image/gif"

        response = httpx.post(
            f"{api_url}/upload",
            files={"file": (image_path.name, f, mime)},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()


def normalize(value: str) -> str:
    return value.lower().strip()


def attribute_match(predicted: str, ground_truth: str) -> bool:
    """Partial-match: predicted contains or equals the ground truth token."""
    p = normalize(predicted)
    g = normalize(ground_truth)
    return g in p or p in g or p == g


def evaluate(api_url: str, images_dir: Path, labels: dict) -> None:
    per_attr_correct = defaultdict(int)
    per_attr_total = defaultdict(int)
    results = []

    image_files = sorted(
        p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    )

    if not image_files:
        print(f"No image files found in {images_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(image_files)} images. Running classification…\n")

    for img_path in image_files:
        label = labels.get(img_path.name)
        if label is None:
            print(f"  SKIP {img_path.name} — no label")
            continue

        print(f"  Classifying {img_path.name}…", end=" ", flush=True)
        try:
            prediction = upload_image(api_url, img_path)
        except Exception as e:
            print(f"FAILED ({e})")
            continue

        row = {"filename": img_path.name, "matches": {}}
        for attr in ATTRIBUTES:
            gt = label.get(attr, "")
            pred = prediction.get(attr, "")
            if gt:
                match = attribute_match(pred, gt)
                per_attr_correct[attr] += int(match)
                per_attr_total[attr] += 1
                row["matches"][attr] = {"predicted": pred, "ground_truth": gt, "match": match}

        all_correct = all(v["match"] for v in row["matches"].values())
        print("OK" if all_correct else "PARTIAL")
        results.append(row)

        # Small delay to avoid rate limits
        time.sleep(1)

    # ── Report ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Per-attribute accuracy")
    print("=" * 60)

    overall_correct = 0
    overall_total = 0
    for attr in ATTRIBUTES:
        total = per_attr_total[attr]
        correct = per_attr_correct[attr]
        if total == 0:
            print(f"  {attr:<22} n/a")
            continue
        acc = correct / total * 100
        bar = "█" * int(acc / 5)
        print(f"  {attr:<22} {acc:5.1f}%  {bar}  ({correct}/{total})")
        overall_correct += correct
        overall_total += total

    print("-" * 60)
    if overall_total:
        overall = overall_correct / overall_total * 100
        print(f"  {'Overall':<22} {overall:5.1f}%  ({overall_correct}/{overall_total})")
    print("=" * 60)

    # Write detailed JSON report
    report_path = Path("eval_report.json")
    report = {
        "per_attribute_accuracy": {
            attr: {
                "correct": per_attr_correct[attr],
                "total": per_attr_total[attr],
                "accuracy": (
                    per_attr_correct[attr] / per_attr_total[attr]
                    if per_attr_total[attr] else None
                ),
            }
            for attr in ATTRIBUTES
        },
        "overall_accuracy": overall_correct / overall_total if overall_total else None,
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nDetailed report written to {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate fashion classifier accuracy.")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--images-dir", default="./test_images", help="Directory of test images")
    parser.add_argument("--labels", default="./labels.json", help="Path to ground-truth labels JSON")
    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    labels_path = Path(args.labels)

    if not images_dir.is_dir():
        print(f"Images directory not found: {images_dir}", file=sys.stderr)
        sys.exit(1)

    if not labels_path.exists():
        print(f"Labels file not found: {labels_path}", file=sys.stderr)
        print("Creating sample labels.json template…")
        sample = {
            "example_shirt.jpg": {attr: "" for attr in ATTRIBUTES}
        }
        labels_path.write_text(json.dumps(sample, indent=2))
        print(f"Edit {labels_path} with ground-truth labels, then re-run.")
        sys.exit(0)

    labels = json.loads(labels_path.read_text())
    evaluate(args.api_url, images_dir, labels)


if __name__ == "__main__":
    main()
