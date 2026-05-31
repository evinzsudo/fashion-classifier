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
        "trend_notes": "Classic wardrobe staple.",
        "location_context": "urban",
        "continent": "",
        "country": "",
        "city": "",
        "designer": "",
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


# ── New contextual filter tests ──────────────────────────────────────────────

def test_filter_by_continent(client, db_session):
    make_garment(db_session, filename="loc1.jpg", continent="Asia")
    make_garment(db_session, filename="loc2.jpg", continent="Europe")

    resp = client.get("/garments", params={"continent": "Asia"})
    data = resp.json()
    assert all(g["continent"] == "Asia" for g in data)
    assert len(data) == 1


def test_filter_by_country(client, db_session):
    make_garment(db_session, filename="ctr1.jpg", country="Japan")
    make_garment(db_session, filename="ctr2.jpg", country="France")

    resp = client.get("/garments", params={"country": "Japan"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["country"] == "Japan"


def test_filter_by_city(client, db_session):
    make_garment(db_session, filename="cty1.jpg", city="Tokyo")
    make_garment(db_session, filename="cty2.jpg", city="Paris")

    resp = client.get("/garments", params={"city": "Tokyo"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["city"] == "Tokyo"


def test_filter_by_designer(client, db_session):
    make_garment(db_session, filename="des1.jpg", designer="Uniqlo")
    make_garment(db_session, filename="des2.jpg", designer="Zara")

    resp = client.get("/garments", params={"designer": "Uniqlo"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["designer"] == "Uniqlo"


def test_filter_by_trend_keyword(client, db_session):
    make_garment(db_session, filename="trnd1.jpg", trend_notes="Very Y2K aesthetic with wide leg silhouette.")
    make_garment(db_session, filename="trnd2.jpg", trend_notes="Classic minimalist cut, timeless appeal.")

    resp = client.get("/garments", params={"trend_keyword": "Y2K"})
    data = resp.json()
    assert len(data) == 1
    assert "Y2K" in data[0]["trend_notes"]


def test_filters_endpoint_includes_location_and_designer(client, db_session):
    make_garment(
        db_session,
        filename="ctx1.jpg",
        continent="Asia",
        country="Japan",
        city="Tokyo",
        designer="Issey Miyake",
    )

    resp = client.get("/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "Asia" in data["continent"]
    assert "Japan" in data["country"]
    assert "Tokyo" in data["city"]
    assert "Issey Miyake" in data["designer"]


def test_filters_endpoint_includes_year_and_month(client, db_session):
    make_garment(db_session, filename="time1.jpg")

    resp = client.get("/filters")
    data = resp.json()
    assert len(data["year"]) >= 1
    assert len(data["month"]) >= 1
    # Year should look like a 4-digit string
    assert all(len(y) == 4 for y in data["year"])
    # Month should be zero-padded 2-digit string
    assert all(len(m) == 2 for m in data["month"])


def test_garment_out_includes_new_fields(client, db_session):
    g = make_garment(
        db_session,
        filename="fields.jpg",
        continent="Europe",
        country="Italy",
        city="Milan",
        designer="Prada",
    )

    resp = client.get(f"/garments/{g.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["continent"] == "Europe"
    assert data["country"] == "Italy"
    assert data["city"] == "Milan"
    assert data["designer"] == "Prada"


# ── Similar garments tests ────────────────────────────────────────────────────

def test_similar_garments_requires_two_matching_attributes(client, db_session):
    """Only garments sharing >= 2 of garment_type, style, season appear in results."""
    source = make_garment(db_session, filename="src.jpg",
                          garment_type="dress", style="casual", season="spring/summer")
    # Shares 3 — should appear
    full_match = make_garment(db_session, filename="fm.jpg",
                              garment_type="dress", style="casual", season="spring/summer")
    # Shares 2 — should appear
    two_match = make_garment(db_session, filename="2m.jpg",
                             garment_type="dress", style="casual", season="fall/winter")
    # Shares only 1 — should NOT appear
    one_match = make_garment(db_session, filename="1m.jpg",
                             garment_type="dress", style="formal", season="fall/winter")

    resp = client.get(f"/garments/{source.id}/similar")
    assert resp.status_code == 200
    ids = [g["id"] for g in resp.json()]
    assert full_match.id in ids
    assert two_match.id in ids
    assert one_match.id not in ids
    assert source.id not in ids  # source is never in its own similar list


def test_similar_garments_excludes_self(client, db_session):
    g = make_garment(db_session, filename="self.jpg",
                     garment_type="jacket", style="minimalist", season="all-season")
    resp = client.get(f"/garments/{g.id}/similar")
    assert resp.status_code == 200
    assert g.id not in [x["id"] for x in resp.json()]


def test_similar_garments_returns_at_most_four(client, db_session):
    make_garment(db_session, filename="base.jpg",
                 garment_type="shirt", style="formal", season="all-season")
    source = make_garment(db_session, filename="s.jpg",
                          garment_type="shirt", style="formal", season="all-season")
    # Create 6 similar garments
    for i in range(6):
        make_garment(db_session, filename=f"sim{i}.jpg",
                     garment_type="shirt", style="formal", season="all-season")

    resp = client.get(f"/garments/{source.id}/similar")
    assert resp.status_code == 200
    assert len(resp.json()) <= 4


def test_similar_garments_returns_404_for_missing(client):
    resp = client.get("/garments/999999/similar")
    assert resp.status_code == 404


def test_similar_garments_returns_empty_when_no_matches(client, db_session):
    lone = make_garment(db_session, filename="lone.jpg",
                        garment_type="unique_type_xyz", style="casual", season="all-season")
    resp = client.get(f"/garments/{lone.id}/similar")
    assert resp.status_code == 200
    assert resp.json() == []
