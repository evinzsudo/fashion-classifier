"""
End-to-end tests for the upload → classify → filter workflow.

The Claude API call is mocked so tests run offline without consuming API credits.
"""
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image


def make_jpeg_bytes(color=(200, 150, 100)) -> bytes:
    img = Image.new("RGB", (80, 80), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


MOCK_RESPONSE_TEXT = json.dumps({
    "description": "A bright red casual hoodie with a kangaroo pocket.",
    "garment_type": "hoodie",
    "style": "casual",
    "material": "cotton blend",
    "color_palette": "solid red",
    "pattern": "solid",
    "season": "fall/winter",
    "occasion": "casual everyday",
    "consumer_profile": "teen trendsetter",
    "trend_notes": "Hoodies remain a streetwear staple with oversized silhouettes trending.",
    "location_context": "urban",
})


def mock_claude_response(text: str):
    content_block = type("Block", (), {"text": text})()
    return type("Msg", (), {"content": [content_block]})()


@pytest.fixture()
def mock_classify():
    with patch("app.backend.classifier.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = type("Messages", (), {})()
        instance.messages.create = AsyncMock(
            return_value=mock_claude_response(MOCK_RESPONSE_TEXT)
        )
        yield MockClient


def test_upload_classify_returns_structured_data(client, mock_classify):
    image_bytes = make_jpeg_bytes()
    resp = client.post(
        "/upload",
        files={"file": ("hoodie.jpg", image_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["garment_type"] == "hoodie"
    assert data["style"] == "casual"
    assert data["material"] == "cotton blend"
    assert data["color_palette"] == "solid red"
    assert data["pattern"] == "solid"
    assert data["season"] == "fall/winter"
    assert data["occasion"] == "casual everyday"
    assert data["consumer_profile"] == "teen trendsetter"
    assert data["location_context"] == "urban"
    assert "hoodie" in data["raw_description"].lower()
    assert data["annotations"] == []
    assert data["id"] is not None
    # New fields default to empty string when not provided
    assert data["continent"] == ""
    assert data["country"] == ""
    assert data["city"] == ""
    assert data["designer"] == ""


def test_upload_with_metadata(client, mock_classify):
    image_bytes = make_jpeg_bytes(color=(150, 150, 200))
    resp = client.post(
        "/upload",
        files={"file": ("hoodie_meta.jpg", image_bytes, "image/jpeg")},
        data={
            "continent": "Europe",
            "country": "France",
            "city": "Paris",
            "designer": "Jacquemus",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["continent"] == "Europe"
    assert data["country"] == "France"
    assert data["city"] == "Paris"
    assert data["designer"] == "Jacquemus"


def test_upload_then_filter(client, mock_classify):
    image_bytes = make_jpeg_bytes(color=(100, 100, 200))
    resp = client.post(
        "/upload",
        files={"file": ("hoodie2.jpg", image_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    garment_id = resp.json()["id"]

    resp = client.get("/garments", params={"garment_type": "hoodie"})
    assert resp.status_code == 200
    ids = [g["id"] for g in resp.json()]
    assert garment_id in ids


def test_upload_with_metadata_then_filter_by_designer(client, mock_classify):
    image_bytes = make_jpeg_bytes(color=(200, 100, 100))
    resp = client.post(
        "/upload",
        files={"file": ("hoodie_des.jpg", image_bytes, "image/jpeg")},
        data={"designer": "A.P.C."},
    )
    garment_id = resp.json()["id"]

    resp = client.get("/garments", params={"designer": "A.P.C."})
    ids = [g["id"] for g in resp.json()]
    assert garment_id in ids

    # Different designer should not appear
    resp2 = client.get("/garments", params={"designer": "Zara"})
    ids2 = [g["id"] for g in resp2.json()]
    assert garment_id not in ids2


def test_filter_by_trend_keyword(client, mock_classify):
    image_bytes = make_jpeg_bytes(color=(80, 180, 80))
    resp = client.post(
        "/upload",
        files={"file": ("hoodie3.jpg", image_bytes, "image/jpeg")},
    )
    garment_id = resp.json()["id"]

    # "oversized" appears in the mock trend_notes
    resp = client.get("/garments", params={"trend_keyword": "oversized"})
    ids = [g["id"] for g in resp.json()]
    assert garment_id in ids

    resp2 = client.get("/garments", params={"trend_keyword": "haute couture ballgown"})
    ids2 = [g["id"] for g in resp2.json()]
    assert garment_id not in ids2


def test_upload_then_search(client, mock_classify):
    image_bytes = make_jpeg_bytes(color=(80, 180, 80))
    resp = client.post(
        "/upload",
        files={"file": ("hoodie_srch.jpg", image_bytes, "image/jpeg")},
    )
    garment_id = resp.json()["id"]

    resp = client.get("/garments", params={"search": "kangaroo pocket"})
    ids = [g["id"] for g in resp.json()]
    assert garment_id in ids


def test_upload_annotate_search_annotation(client, mock_classify):
    image_bytes = make_jpeg_bytes(color=(200, 80, 80))
    upload = client.post(
        "/upload",
        files={"file": ("hoodie4.jpg", image_bytes, "image/jpeg")},
    )
    garment_id = upload.json()["id"]

    ann_resp = client.post(
        f"/garments/{garment_id}/annotations",
        json={"text": "Spotted at Berlin Fashion Week", "author": "editor"},
    )
    assert ann_resp.status_code == 200
    assert ann_resp.json()["annotations"][0]["text"] == "Spotted at Berlin Fashion Week"

    search = client.get("/garments", params={"search": "Berlin Fashion Week"})
    ids = [g["id"] for g in search.json()]
    assert garment_id in ids


def test_upload_rejected_for_non_image(client):
    resp = client.post(
        "/upload",
        files={"file": ("data.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400


def test_filters_populated_after_upload(client, mock_classify):
    image_bytes = make_jpeg_bytes()
    client.post(
        "/upload",
        files={"file": ("hoodie5.jpg", image_bytes, "image/jpeg")},
        data={"continent": "North America", "city": "New York", "designer": "Ralph Lauren"},
    )

    resp = client.get("/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "hoodie" in data["garment_type"]
    assert "casual" in data["style"]
    assert "urban" in data["location_context"]
    assert "North America" in data["continent"]
    assert "New York" in data["city"]
    assert "Ralph Lauren" in data["designer"]
    assert len(data["year"]) >= 1
    assert len(data["month"]) >= 1
