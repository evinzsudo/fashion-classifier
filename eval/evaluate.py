#!/usr/bin/env python3
"""Evaluation script for the fashion classifier.

Normal mode   — uploads each image to a running backend via HTTP.
Dry-run mode  — imports the classifier directly and classifies images
                without storing anything to the database.

Usage
-----
# Normal (requires `make run-backend` first):
python eval/evaluate.py --api-url http://localhost:8000 \\
                        --images-dir ./test_images \\
                        --labels ./labels.json

# Dry-run (no running backend, no DB writes, needs ANTHROPIC_API_KEY):
python eval/evaluate.py --images-dir ./test_images \\
                        --labels ./labels.json \\
                        --dry-run

labels.json format
------------------
{
  "shirt_001.jpg": {
    "garment_type": "shirt",
    "style": "casual",
    "material": "cotton",
    ...
  }
}
Leave any field as "" to exclude it from accuracy calculation.
"""

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

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

# ── Classification helpers ────────────────────────────────────────────────────

def _mime(image_path: Path) -> str:
    return {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(
        image_path.suffix.lower(), "image/jpeg"
    )


def upload_and_classify(api_url: str, image_path: Path) -> dict:
    """Upload *image_path* to the running backend and return the GarmentOut dict."""
    with open(image_path, "rb") as f:
        response = httpx.post(
            f"{api_url}/upload",
            files={"file": (image_path.name, f, _mime(image_path))},
            timeout=90.0,
        )
        response.raise_for_status()
        return response.json()


async def _classify_direct_async(image_path: Path) -> dict:
    """Classify *image_path* by importing the backend classifier directly (no DB writes)."""
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.backend.classifier import classify_image
    from app.backend.normalizer import normalize_attributes

    image_bytes = image_path.read_bytes()
    description, attrs = await classify_image(image_bytes, _mime(image_path))
    normalized = normalize_attributes(attrs)
    return {"raw_description": description, **normalized}


def classify_direct(image_path: Path) -> dict:
    """Synchronous wrapper for dry-run classification."""
    return asyncio.run(_classify_direct_async(image_path))


# ── Matching logic ────────────────────────────────────────────────────────────

def _normalize(value: str) -> str:
    return value.lower().strip()


def attribute_match(predicted: str, ground_truth: str) -> bool:
    """Partial-match: at least one value contains the other."""
    p = _normalize(predicted)
    g = _normalize(ground_truth)
    return g in p or p in g or p == g


# ── Plain-English summary ─────────────────────────────────────────────────────

_HARD_REASONS = {
    "material":         "Tactile properties (texture, weight, drape) are invisible in photographs.",
    "style":            "Style is a culturally loaded judgment that varies across designers and markets.",
    "consumer_profile": "Consumer profile is subjective and inherits errors from style predictions.",
    "occasion":         "Category boundaries (casual / business casual) are fuzzy and context-dependent.",
}


def generate_summary(correct: dict, total: dict) -> str:
    lines = ["\n" + "=" * 60, "Summary", "=" * 60]

    ranked = [
        (attr, correct[attr] / total[attr])
        for attr in ATTRIBUTES
        if total[attr] > 0
    ]
    ranked.sort(key=lambda x: -x[1])

    strong = [(a, v) for a, v in ranked if v >= 0.70]
    moderate = [(a, v) for a, v in ranked if 0.50 <= v < 0.70]
    weak = [(a, v) for a, v in ranked if v < 0.50]

    if strong:
        attrs = ", ".join(f"{a} ({v:.0%})" for a, v in strong)
        lines.append(f"\nStrong  (≥70%): {attrs}")
        lines.append(
            "  These attributes have clear, unambiguous visual signals in photographs."
        )

    if moderate:
        attrs = ", ".join(f"{a} ({v:.0%})" for a, v in moderate)
        lines.append(f"\nModerate (50–70%): {attrs}")

    if weak:
        attrs = ", ".join(f"{a} ({v:.0%})" for a, v in weak)
        lines.append(f"\nStruggles (<50%): {attrs}")
        for attr, _ in weak:
            if attr in _HARD_REASONS:
                lines.append(f"  {attr}: {_HARD_REASONS[attr]}")

    lines += [
        "\nTo improve accuracy:",
        "  • Provide richer context in the upload form (designer, occasion).",
        "  • Use well-lit images where the garment fills most of the frame.",
        "  • Add few-shot examples of edge cases to the classification prompt.",
        "=" * 60,
    ]
    return "\n".join(lines)


# ── Main evaluation loop ──────────────────────────────────────────────────────

def evaluate(
    api_url: str,
    images_dir: Path,
    labels: dict,
    dry_run: bool,
) -> None:
    per_attr_correct: defaultdict[str, int] = defaultdict(int)
    per_attr_total: defaultdict[str, int] = defaultdict(int)
    results = []

    image_files = sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    )

    if not image_files:
        print(f"No image files found in {images_dir}", file=sys.stderr)
        sys.exit(1)

    mode = "dry-run (no DB writes)" if dry_run else f"API  {api_url}"
    print(f"Found {len(image_files)} images.  Mode: {mode}\n")

    for img_path in image_files:
        label = labels.get(img_path.name)
        if label is None:
            print(f"  SKIP  {img_path.name} — no label")
            continue

        print(f"  {'[dry]' if dry_run else '[api]'}  {img_path.name}…", end=" ", flush=True)
        try:
            prediction = (
                classify_direct(img_path)
                if dry_run
                else upload_and_classify(api_url, img_path)
            )
        except Exception as e:
            print(f"FAILED ({e})")
            continue

        row: dict = {"filename": img_path.name, "matches": {}}
        for attr in ATTRIBUTES:
            gt = label.get(attr, "")
            pred = prediction.get(attr, "")
            if not gt:
                continue
            match = attribute_match(pred, gt)
            per_attr_correct[attr] += int(match)
            per_attr_total[attr] += 1
            row["matches"][attr] = {"predicted": pred, "ground_truth": gt, "match": match}

        all_ok = all(v["match"] for v in row["matches"].values())
        print("✓" if all_ok else "~")
        results.append(row)

        if not dry_run:
            time.sleep(1)  # stay within Anthropic free-tier rate limits

    # ── Per-attribute accuracy table ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Per-attribute accuracy")
    print("=" * 60)

    overall_correct = overall_total = 0
    for attr in ATTRIBUTES:
        n = per_attr_total[attr]
        c = per_attr_correct[attr]
        if n == 0:
            print(f"  {attr:<24} n/a")
            continue
        acc = c / n
        bar = "█" * int(acc * 20)
        print(f"  {attr:<24} {acc:5.1%}  {bar:<20}  ({c}/{n})")
        overall_correct += c
        overall_total += n

    print("-" * 60)
    if overall_total:
        overall = overall_correct / overall_total
        print(f"  {'Overall':<24} {overall:5.1%}  ({overall_correct}/{overall_total})")
    print("=" * 60)

    print(generate_summary(per_attr_correct, per_attr_total))

    # ── Save timestamped JSON report ──────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(f"eval_report_{ts}.json")
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry_run" if dry_run else "api",
        "images_evaluated": len(results),
        "overall_accuracy": overall_correct / overall_total if overall_total else None,
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
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nDetailed report saved to {report_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate fashion classifier accuracy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--api-url",     default="http://localhost:8000",
                        help="Backend API base URL (ignored in --dry-run mode)")
    parser.add_argument("--images-dir",  default="./test_images",
                        help="Directory of test images")
    parser.add_argument("--labels",      default="./labels.json",
                        help="Path to ground-truth labels JSON")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Classify directly via the Python module — no backend, no DB writes")
    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    labels_path = Path(args.labels)

    if not images_dir.is_dir():
        print(f"Images directory not found: {images_dir}", file=sys.stderr)
        sys.exit(1)

    if not labels_path.exists():
        print(f"Labels file not found: {labels_path}", file=sys.stderr)
        sample = {"example_shirt.jpg": {attr: "" for attr in ATTRIBUTES}}
        labels_path.write_text(json.dumps(sample, indent=2))
        print(f"Created template at {labels_path}. Fill in ground-truth values and re-run.")
        sys.exit(0)

    labels = json.loads(labels_path.read_text())
    evaluate(args.api_url, images_dir, labels, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
