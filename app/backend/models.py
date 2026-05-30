from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from .database import Base


class Garment(Base):
    __tablename__ = "garments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    original_filename = Column(String)
    upload_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # AI output
    raw_description = Column(Text, default="")
    garment_type = Column(String, default="")
    style = Column(String, default="")
    material = Column(String, default="")
    color_palette = Column(String, default="")
    pattern = Column(String, default="")
    season = Column(String, default="")
    occasion = Column(String, default="")
    consumer_profile = Column(String, default="")
    trend_notes = Column(Text, default="")
    location_context = Column(String, default="")

    # User annotations stored as JSON list of {text, author, created_at}
    annotations = Column(JSON, default=list)
