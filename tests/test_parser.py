"""Unit tests for classifier output parsing."""
import json
import pytest
from app.backend.classifier import extract_json, CLASSIFICATION_PROMPT

EXPECTED_KEYS = {
    "garment_type", "style", "material", "color_palette", "pattern",
    "season", "occasion", "consumer_profile", "trend_notes", "location_context",
}

SAMPLE_ATTRS = {
    "description": "A crisp white button-down shirt with a slim fit.",
    "garment_type": "shirt",
    "style": "business casual",
    "material": "cotton",
    "color_palette": "solid white",
    "pattern": "solid",
    "season": "all-season",
    "occasion": "business casual",
    "consumer_profile": "young professional",
    "trend_notes": "Classic staple with enduring appeal.",
    "location_context": "urban",
}


def test_extract_plain_json():
    text = json.dumps(SAMPLE_ATTRS)
    result = extract_json(text)
    assert result["garment_type"] == "shirt"
    assert result["style"] == "business casual"


def test_extract_json_with_markdown_fences():
    text = f"```json\n{json.dumps(SAMPLE_ATTRS)}\n```"
    result = extract_json(text)
    assert result["material"] == "cotton"


def test_extract_json_with_leading_text():
    text = "Here is the analysis:\n" + json.dumps(SAMPLE_ATTRS)
    result = extract_json(text)
    assert result["pattern"] == "solid"


def test_extract_json_with_trailing_text():
    text = json.dumps(SAMPLE_ATTRS) + "\n\nLet me know if you need anything else."
    result = extract_json(text)
    assert result["season"] == "all-season"


def test_extract_json_missing_raises():
    with pytest.raises((ValueError, Exception)):
        extract_json("This is just plain text with no JSON.")


def test_extract_json_preserves_all_keys():
    text = json.dumps(SAMPLE_ATTRS)
    result = extract_json(text)
    for key in EXPECTED_KEYS:
        assert key in result, f"Missing key: {key}"


def test_extract_json_whitespace_only_description():
    data = {**SAMPLE_ATTRS, "description": "   "}
    text = json.dumps(data)
    result = extract_json(text)
    assert result["description"].strip() == ""


def test_classification_prompt_mentions_all_fields():
    """Prompt must request each attribute field."""
    for key in EXPECTED_KEYS:
        assert key in CLASSIFICATION_PROMPT, f"Prompt missing field: {key}"
