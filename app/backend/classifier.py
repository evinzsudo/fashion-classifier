"""Claude vision API integration for garment classification."""

import json
import re
import base64
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-4-20250514"

CLASSIFICATION_PROMPT = """\
Analyze this fashion garment image and return a single JSON object.

CONSTRAINTS — you MUST use exactly one of these values:
  style: casual | formal | minimalist | bohemian | athletic | streetwear | vintage | preppy | romantic | avant-garde
  color_palette: neutral earth tones | bold primary colors | pastels | monochrome | warm tones | cool tones | black and white | mixed

OUTPUT SCHEMA:
{
  "description": "2-3 sentence natural language description",
  "garment_type": "e.g. dress, shirt, pants, jacket, skirt, coat, blazer, hoodie, jeans",
  "style": "<one of the 10 constrained values above>",
  "material": "e.g. cotton, denim, silk, wool, linen, leather, polyester, cotton blend",
  "color_palette": "<one of the 8 constrained values above>",
  "pattern": "e.g. solid, stripes, floral, plaid, geometric, abstract, animal print, polka dots",
  "season": "e.g. spring/summer, fall/winter, all-season",
  "occasion": "e.g. casual everyday, business casual, formal event, athletic, beach, evening",
  "consumer_profile": "e.g. young professional, teen trendsetter, mature classic, outdoor enthusiast",
  "trend_notes": "1-2 sentences on trend relevance or notable design elements",
  "location_context": "e.g. urban, beach, office, outdoor/adventure, resort, gym",
  "confidence": {
    "garment_type": 0.0-1.0,
    "style": 0.0-1.0,
    "material": 0.0-1.0,
    "color_palette": 0.0-1.0,
    "pattern": 0.0-1.0,
    "season": 0.0-1.0,
    "occasion": 0.0-1.0,
    "consumer_profile": 0.0-1.0,
    "trend_notes": 0.0-1.0,
    "location_context": 0.0-1.0
  }
}

EXAMPLES:

Example 1 — floral midi dress:
{
  "description": "A flowing midi dress with a delicate floral print in soft pink and white tones. Features a V-neck, flutter sleeves, and a tiered skirt with a relaxed feminine silhouette.",
  "garment_type": "dress",
  "style": "romantic",
  "material": "rayon",
  "color_palette": "pastels",
  "pattern": "floral",
  "season": "spring/summer",
  "occasion": "casual everyday",
  "consumer_profile": "young professional",
  "trend_notes": "Cottagecore-inspired florals remain strong, pairing well with strappy sandals for a versatile daytime look.",
  "location_context": "urban",
  "confidence": {"garment_type": 0.99, "style": 0.88, "material": 0.71, "color_palette": 0.94, "pattern": 0.98, "season": 0.92, "occasion": 0.79, "consumer_profile": 0.72, "trend_notes": 0.85, "location_context": 0.68}
}

Example 2 — structured blazer:
{
  "description": "A tailored double-breasted blazer in charcoal grey with subtle pinstripe detailing. Structured shoulders, notch lapels, and a fitted waist create a sharp professional silhouette.",
  "garment_type": "blazer",
  "style": "formal",
  "material": "wool",
  "color_palette": "monochrome",
  "pattern": "pinstripe",
  "season": "fall/winter",
  "occasion": "business casual",
  "consumer_profile": "young professional",
  "trend_notes": "Oversized blazers remain a wardrobe staple, transitioning easily from boardroom to evening events.",
  "location_context": "office",
  "confidence": {"garment_type": 0.97, "style": 0.91, "material": 0.69, "color_palette": 0.88, "pattern": 0.84, "season": 0.87, "occasion": 0.83, "consumer_profile": 0.80, "trend_notes": 0.82, "location_context": 0.90}
}

Example 3 — distressed jeans:
{
  "description": "High-waisted straight-leg jeans in a medium blue wash with distressed detailing at the knees. Classic five-pocket construction with a relaxed, effortless aesthetic.",
  "garment_type": "jeans",
  "style": "casual",
  "material": "denim",
  "color_palette": "cool tones",
  "pattern": "solid",
  "season": "all-season",
  "occasion": "casual everyday",
  "consumer_profile": "teen trendsetter",
  "trend_notes": "Straight-leg and barrel-fit jeans are at peak trend, replacing slim cuts across demographics.",
  "location_context": "urban",
  "confidence": {"garment_type": 0.99, "style": 0.95, "material": 0.98, "color_palette": 0.85, "pattern": 0.93, "season": 0.88, "occasion": 0.90, "consumer_profile": 0.67, "trend_notes": 0.88, "location_context": 0.75}
}

Return ONLY valid JSON — no markdown fences, no extra text.\
"""


def extract_json(text: str) -> dict[str, Any]:
    """Parse JSON from a Claude response, stripping markdown fences if present.

    Raises:
        ValueError: If no JSON object can be found in *text*.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON object found in response: {text[:300]}")


async def classify_image(
    image_bytes: bytes,
    media_type: str,
) -> tuple[str, dict[str, Any], dict[str, float] | None]:
    """Send *image_bytes* to Claude and return ``(description, attributes_dict, confidence_dict)``.

    Args:
        image_bytes: Raw bytes of the image file.
        media_type:  MIME type, e.g. ``"image/jpeg"``.

    Returns:
        A 3-tuple of: natural-language description, dict of ten structured
        attribute fields, and an optional dict mapping each attribute to a
        0.0–1.0 confidence score.

    Raises:
        anthropic.AuthenticationError: API key is missing or invalid.
        anthropic.APITimeoutError:     Request timed out.
        anthropic.RateLimitError:      Anthropic API rate limit hit.
        anthropic.BadRequestError:     Image rejected by the API (too large, etc.).
        ValueError:                    Claude response could not be parsed as JSON.
    """
    client = AsyncAnthropic()
    b64 = base64.standard_b64encode(image_bytes).decode()

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": CLASSIFICATION_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    data = extract_json(raw_text)
    description = data.pop("description", raw_text)
    confidence = data.pop("confidence", None)
    return description, data, confidence
