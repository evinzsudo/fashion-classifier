"""Claude vision API integration for garment classification.

Single API call returns a natural-language description alongside all ten
structured attributes.  The prompt asks for a JSON-only response; the
extract_json() fallback handles stray markdown fences or preamble text.
"""

import json
import re
import base64
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-4-20250514"

CLASSIFICATION_PROMPT = """\
Analyze this fashion garment image and return a single JSON object with exactly these fields:

{
  "description": "2-3 sentence natural language description of the garment",
  "garment_type": "e.g. dress, shirt, pants, jacket, skirt, coat, blouse, shorts",
  "style": "e.g. casual, formal, streetwear, bohemian, minimalist, preppy, athletic",
  "material": "e.g. cotton, polyester, denim, silk, wool, linen, leather, synthetic blend",
  "color_palette": "e.g. monochromatic black, earth tones, pastel pink and white, navy and cream",
  "pattern": "e.g. solid, stripes, floral, plaid, geometric, abstract, animal print, polka dots",
  "season": "e.g. spring/summer, fall/winter, all-season",
  "occasion": "e.g. casual everyday, business casual, formal event, athletic, beach, evening",
  "consumer_profile": "e.g. young professional, teen trendsetter, mature classic, outdoor enthusiast",
  "trend_notes": "1-2 sentences on trend relevance, styling suggestions, or notable design elements",
  "location_context": "e.g. urban, beach, office, outdoor/adventure, resort, gym"
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
) -> tuple[str, dict[str, Any]]:
    """Send *image_bytes* to Claude and return ``(description, attributes_dict)``.

    Args:
        image_bytes: Raw bytes of the image file.
        media_type:  MIME type, e.g. ``"image/jpeg"``.

    Returns:
        A 2-tuple of the natural-language description string and a dict of the
        ten structured attribute fields.

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
    return description, data
