import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from sqlalchemy.orm.attributes import flag_modified

from dotenv import load_dotenv

load_dotenv()

from .database import engine, get_db, Base
from .models import Garment
from .schemas import GarmentOut, AnnotationCreate, FilterOptions
from .classifier import classify_image

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fashion Classifier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post("/upload", response_model=GarmentOut)
async def upload_garment(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, WebP, and GIF images are supported.")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE:
        raise HTTPException(400, "Image must be under 10 MB.")

    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    (UPLOAD_DIR / filename).write_bytes(image_bytes)

    try:
        raw_description, attrs = await classify_image(image_bytes, file.content_type)
    except Exception as exc:
        (UPLOAD_DIR / filename).unlink(missing_ok=True)
        raise HTTPException(502, f"Classification failed: {exc}") from exc

    garment = Garment(
        filename=filename,
        original_filename=file.filename,
        raw_description=raw_description,
        garment_type=attrs.get("garment_type", ""),
        style=attrs.get("style", ""),
        material=attrs.get("material", ""),
        color_palette=attrs.get("color_palette", ""),
        pattern=attrs.get("pattern", ""),
        season=attrs.get("season", ""),
        occasion=attrs.get("occasion", ""),
        consumer_profile=attrs.get("consumer_profile", ""),
        trend_notes=attrs.get("trend_notes", ""),
        location_context=attrs.get("location_context", ""),
        annotations=[],
    )
    db.add(garment)
    db.commit()
    db.refresh(garment)
    return garment


@app.get("/garments", response_model=List[GarmentOut])
def list_garments(
    search: Optional[str] = Query(None),
    garment_type: Optional[str] = Query(None),
    style: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    color_palette: Optional[str] = Query(None),
    pattern: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    occasion: Optional[str] = Query(None),
    consumer_profile: Optional[str] = Query(None),
    location_context: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Garment)

    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Garment.raw_description.ilike(term),
                Garment.garment_type.ilike(term),
                Garment.style.ilike(term),
                Garment.material.ilike(term),
                Garment.color_palette.ilike(term),
                Garment.pattern.ilike(term),
                Garment.occasion.ilike(term),
                Garment.trend_notes.ilike(term),
                cast(Garment.annotations, String).ilike(term),
            )
        )

    exact_filters = {
        "garment_type": garment_type,
        "style": style,
        "material": material,
        "color_palette": color_palette,
        "pattern": pattern,
        "season": season,
        "occasion": occasion,
        "consumer_profile": consumer_profile,
        "location_context": location_context,
    }
    for field, value in exact_filters.items():
        if value:
            q = q.filter(getattr(Garment, field) == value)

    return q.order_by(Garment.upload_time.desc()).all()


@app.get("/garments/{garment_id}", response_model=GarmentOut)
def get_garment(garment_id: int, db: Session = Depends(get_db)):
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        raise HTTPException(404, "Garment not found.")
    return garment


@app.post("/garments/{garment_id}/annotations", response_model=GarmentOut)
def add_annotation(
    garment_id: int, annotation: AnnotationCreate, db: Session = Depends(get_db)
):
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        raise HTTPException(404, "Garment not found.")

    entry = {
        "text": annotation.text.strip(),
        "author": annotation.author or "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    garment.annotations = (garment.annotations or []) + [entry]
    flag_modified(garment, "annotations")
    db.commit()
    db.refresh(garment)
    return garment


@app.delete("/garments/{garment_id}/annotations/{index}", response_model=GarmentOut)
def delete_annotation(
    garment_id: int, index: int, db: Session = Depends(get_db)
):
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        raise HTTPException(404, "Garment not found.")

    annotations = list(garment.annotations or [])
    if index < 0 or index >= len(annotations):
        raise HTTPException(400, "Invalid annotation index.")

    garment.annotations = [a for i, a in enumerate(annotations) if i != index]
    flag_modified(garment, "annotations")
    db.commit()
    db.refresh(garment)
    return garment


@app.get("/filters", response_model=FilterOptions)
def get_filters(db: Session = Depends(get_db)):
    def distinct(col):
        return sorted({v for (v,) in db.query(col).distinct().all() if v})

    return FilterOptions(
        garment_type=distinct(Garment.garment_type),
        style=distinct(Garment.style),
        material=distinct(Garment.material),
        color_palette=distinct(Garment.color_palette),
        pattern=distinct(Garment.pattern),
        season=distinct(Garment.season),
        occasion=distinct(Garment.occasion),
        consumer_profile=distinct(Garment.consumer_profile),
        location_context=distinct(Garment.location_context),
    )


@app.get("/images/{filename}")
def serve_image(filename: str):
    # Prevent path traversal
    safe = Path(filename).name
    file_path = UPLOAD_DIR / safe
    if not file_path.exists():
        raise HTTPException(404, "Image not found.")
    return FileResponse(file_path)
