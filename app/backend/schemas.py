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
    annotations: List[Any]

    model_config = {"from_attributes": True}


class FilterOptions(BaseModel):
    garment_type: List[str]
    style: List[str]
    material: List[str]
    color_palette: List[str]
    pattern: List[str]
    season: List[str]
    occasion: List[str]
    consumer_profile: List[str]
    location_context: List[str]
