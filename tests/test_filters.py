"""Integration tests for filter and search API behavior."""
import pytest
from datetime import datetime, timezone

from app.backend.models import Garment


def make_garment(db, **overrides):
    defaults = {
        "filename": f"test_{datetime.now(timezone.utc).timestamp()}.jpg",
        "original_filename": "test.jpg",
        "raw_description": "A sample garment.",
        "garment_type": "shirt",
        "style": "casual",
        "material": "cotton",
        "color_palette": "solid white",
        "pattern": "solid",
        "season": "all-season",
        "occasion": "casual everyday",
        "consumer_profile": "young professional",
        "trend_notes": "Classic.",
        "location_context": "urban",
        "annotations": [],
    }
    defaults.update(overrides)
    g = Garment(**defaults)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def test_list_garments_empty(client):
    resp = client.get("/garments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_filter_by_garment_type(client, db_session):
    make_garment(db_session, filename="g1.jpg", garment_type="dress")
    make_garment(db_session, filename="g2.jpg", garment_type="jacket")

    resp = client.get("/garments", params={"garment_type": "dress"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["garment_type"] == "dress"


def test_filter_by_style(client, db_session):
    make_garment(db_session, filename="s1.jpg", style="formal")
    make_garment(db_session, filename="s2.jpg", style="streetwear")

    resp = client.get("/garments", params={"style": "formal"})
    data = resp.json()
    assert all(g["style"] == "formal" for g in data)


def test_combined_filters(client, db_session):
    make_garment(db_session, filename="c1.jpg", garment_type="dress", season="spring/summer")
    make_garment(db_session, filename="c2.jpg", garment_type="dress", season="fall/winter")
    make_garment(db_session, filename="c3.jpg", garment_type="jacket", season="spring/summer")

    resp = client.get("/garments", params={"garment_type": "dress", "season": "spring/summer"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["filename"] == "c1.jpg"


def test_search_by_description(client, db_session):
    make_garment(db_session, filename="srch1.jpg", raw_description="A vintage denim jacket.")
    make_garment(db_session, filename="srch2.jpg", raw_description="A floral silk blouse.")

    resp = client.get("/garments", params={"search": "denim"})
    data = resp.json()
    assert len(data) == 1
    assert "denim" in data[0]["raw_description"]


def test_search_by_annotation(client, db_session):
    make_garment(
        db_session,
        filename="ann1.jpg",
        annotations=[{"text": "Great for summer festivals", "author": "tester", "created_at": "2025-01-01T00:00:00"}],
    )
    make_garment(db_session, filename="ann2.jpg", annotations=[])

    resp = client.get("/garments", params={"search": "festival"})
    data = resp.json()
    assert len(data) == 1


def test_filters_endpoint_returns_dynamic_options(client, db_session):
    make_garment(db_session, filename="fo1.jpg", garment_type="coat", style="minimalist")
    make_garment(db_session, filename="fo2.jpg", garment_type="shorts", style="athletic")

    resp = client.get("/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "coat" in data["garment_type"]
    assert "shorts" in data["garment_type"]
    assert "minimalist" in data["style"]
    assert "athletic" in data["style"]


def test_add_annotation(client, db_session):
    g = make_garment(db_session, filename="an_add.jpg")
    resp = client.post(
        f"/garments/{g.id}/annotations",
        json={"text": "Needs restyling", "author": "designer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["text"] == "Needs restyling"
    assert data["annotations"][0]["author"] == "designer"


def test_delete_annotation(client, db_session):
    g = make_garment(
        db_session,
        filename="an_del.jpg",
        annotations=[
            {"text": "First note", "author": "a", "created_at": "2025-01-01T00:00:00"},
            {"text": "Second note", "author": "b", "created_at": "2025-01-01T00:00:00"},
        ],
    )
    resp = client.delete(f"/garments/{g.id}/annotations/0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["annotations"]) == 1
    assert data["annotations"][0]["text"] == "Second note"


def test_delete_annotation_invalid_index(client, db_session):
    g = make_garment(db_session, filename="an_bad.jpg", annotations=[])
    resp = client.delete(f"/garments/{g.id}/annotations/99")
    assert resp.status_code == 400
