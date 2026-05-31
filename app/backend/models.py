"""SQLAlchemy ORM model for the garments table."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from .database import Base


class Garment(Base):
    """A single garment record with AI-inferred attributes, user context, and annotations."""

    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)       # UUID-based filename on disk
    original_filename = Column(String)                        # Original upload filename

    upload_time = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # ── AI-inferred attributes ──────────────────────────────────────────────
    raw_description = Column(Text, default="")
    garment_type = Column(String, default="", index=True)
    style = Column(String, default="")
    material = Column(String, default="")
    color_palette = Column(String, default="")
    pattern = Column(String, default="")
    season = Column(String, default="")
    occasion = Column(String, default="")
    consumer_profile = Column(String, default="")
    trend_notes = Column(Text, default="")
    location_context = Column(String, default="")

    # ── User-supplied context at upload time ────────────────────────────────
    continent = Column(String, default="")
    country = Column(String, default="")
    city = Column(String, default="")
    designer = Column(String, default="")

    # ── User annotations ────────────────────────────────────────────────────
    # Stored as JSON list of {text: str, author: str, created_at: str}
    annotations = Column(JSON, default=list)
