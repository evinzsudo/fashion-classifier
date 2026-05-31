from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class AnnotationCreate(BaseModel):
    text: str
    author: Optional[str] = "user"


class GarmentOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    upload_time: datetime
    # AI-inferred
    raw_description: str
    garment_type: str
    style: str
    material: str
    color_palette: str
    pattern: str
    season: str
    occasion: str
    consumer_profile: str
    trend_notes: str
    location_context: str
    # User-supplied
    continent: str
    country: str
    city: str
    designer: str
    annotations: List[Any]
    # Cache metadata (not stored in DB; populated dynamically by upload endpoint)
    from_cache: bool = False
    confidence: Optional[dict] = None

    model_config = {"from_attributes": True}


class FilterOptions(BaseModel):
    # AI-inferred attribute filters
    garment_type: List[str]
    style: List[str]
    material: List[str]
    color_palette: List[str]
    pattern: List[str]
    season: List[str]
    occasion: List[str]
    consumer_profile: List[str]
    location_context: List[str]
    # User-supplied contextual filters
    continent: List[str]
    country: List[str]
    city: List[str]
    designer: List[str]
    # Time filters derived from upload_time
    year: List[str]
    month: List[str]
