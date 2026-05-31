"""FastAPI application for the Fashion Classifier.

Start-up sequence
-----------------
1. Load .env and validate required environment variables.
2. Create / migrate the SQLite database schema.
3. Normalize attribute values in any pre-existing rows.
4. Register HTTP middleware (request logging, CORS).
5. Mount all API routes.
"""

import hashlib
import io
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, DefaultDict, Optional, List

import anthropic as anthropic_sdk
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import cast, func, or_, String, text as sql_text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

load_dotenv()

from .database import engine, get_db, Base, SessionLocal
from .models import Garment
from .schemas import GarmentOut, AnnotationCreate, FilterOptions
from .classifier import classify_image
from .normalizer import normalize_attributes

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-5s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("fashion")

# ── Constants ─────────────────────────────────────────────────────────────────

UPLOAD_DIR = Path(__file__).parent / "uploads"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_NORM_FIELDS = ["garment_type", "material", "style", "occasion", "consumer_profile"]

# ── Rate limiter ──────────────────────────────────────────────────────────────

_RATE_LIMIT = 10          # max uploads per window
_RATE_WINDOW = 60.0       # seconds
_upload_windows: DefaultDict[str, list[float]] = defaultdict(list)


def _allow_upload(client_ip: str) -> bool:
    """Return True when the request is within the per-IP rate limit."""
    now = time.monotonic()
    window = [t for t in _upload_windows[client_ip] if now - t < _RATE_WINDOW]
    if len(window) >= _RATE_LIMIT:
        return False
    window.append(now)
    _upload_windows[client_ip] = window
    return True

# ── Start-up helpers ──────────────────────────────────────────────────────────

def _check_environment() -> None:
    """Print which environment variables are set or missing and exit if critical ones are absent."""
    print("\n─── Fashion Classifier ──────────────────────────────────")
    checks: list[tuple[str, bool, str]] = [
        ("ANTHROPIC_API_KEY", True,  "Required — AI classification will fail without it"),
        ("PEXELS_API_KEY",    False, "Optional — needed for eval/download_test_images.py"),
    ]
    missing_required = False
    for var, required, note in checks:
        val = os.getenv(var, "")
        if val:
            masked = val[:8] + "…" if len(val) > 8 else val
            print(f"  ✓  {var} ({masked})")
        elif required:
            print(f"  ✗  {var} — MISSING  ← {note}")
            print(f"     Add to .env:  {var}=your_key_here")
            missing_required = True
        else:
            print(f"  ·  {var} — not set  ({note})")
    print("─────────────────────────────────────────────────────────\n")
    if missing_required:
        log.warning("ANTHROPIC_API_KEY is not set — /upload will return 500 until it is configured.")


def _migrate(eng) -> None:
    """Idempotently add columns introduced after initial schema creation."""
    new_cols = [
        "ALTER TABLE garments ADD COLUMN continent  TEXT DEFAULT ''",
        "ALTER TABLE garments ADD COLUMN country    TEXT DEFAULT ''",
        "ALTER TABLE garments ADD COLUMN city       TEXT DEFAULT ''",
        "ALTER TABLE garments ADD COLUMN designer   TEXT DEFAULT ''",
        "ALTER TABLE garments ADD COLUMN file_hash  TEXT",
        "ALTER TABLE garments ADD COLUMN confidence TEXT",
    ]
    with eng.connect() as conn:
        for stmt in new_cols:
            try:
                conn.execute(sql_text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists
        # Non-unique index on file_hash (NULLs for legacy rows are fine)
        try:
            conn.execute(sql_text(
                "CREATE INDEX IF NOT EXISTS ix_garments_file_hash ON garments(file_hash)"
            ))
            conn.commit()
        except Exception:
            pass


def _normalize_existing() -> None:
    """Apply attribute normalization to all rows that pre-date the normalizer."""
    db = SessionLocal()
    try:
        updated = 0
        for g in db.query(Garment).all():
            before = {f: (getattr(g, f) or "") for f in _NORM_FIELDS}
            after = normalize_attributes(before)
            if any(after.get(f) != before[f] for f in _NORM_FIELDS):
                for f in _NORM_FIELDS:
                    setattr(g, f, after.get(f, before[f]))
                updated += 1
        if updated:
            db.commit()
            log.info("Normalized %d existing garment records.", updated)
    finally:
        db.close()


# ── Bootstrap ─────────────────────────────────────────────────────────────────

_check_environment()
Base.metadata.create_all(bind=engine)
UPLOAD_DIR.mkdir(exist_ok=True)
_migrate(engine)
_normalize_existing()

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(title="Fashion Classifier API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log method, path, status code, and response time for every request."""
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    log.info("%-6s %-40s %d  %.0f ms",
             request.method, request.url.path, response.status_code, ms)
    return response


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health_check() -> dict:
    """Return API liveness status and whether the Anthropic key is configured."""
    return {
        "status": "ok",
        "anthropic_api_key": "configured" if os.getenv("ANTHROPIC_API_KEY") else "missing — set in .env",
        "version": "1.0.0",
    }


# ── Upload ────────────────────────────────────────────────────────────────────

def _validate_image(data: bytes, filename: str) -> None:
    """Raise HTTP 400 if *data* is not a readable image.

    Uses Pillow so corrupted or truncated files are rejected before
    they reach the Claude API.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise HTTPException(
            400,
            f"'{filename}' could not be read as an image. "
            "The file may be corrupted or in an unsupported format.",
        )


@app.post("/upload", response_model=GarmentOut, tags=["garments"])
async def upload_garment(
    request: Request,
    file: UploadFile = File(...),
    continent: str = Form(default=""),
    country: str = Form(default=""),
    city: str = Form(default=""),
    designer: str = Form(default=""),
    db: Session = Depends(get_db),
) -> GarmentOut:
    """Upload an image, classify it with Claude, and persist the result.

    Rate limited to 10 requests per minute per IP address.
    """
    client_ip = (request.client.host or "unknown") if request.client else "unknown"
    if not _allow_upload(client_ip):
        raise HTTPException(
            429,
            "Upload rate limit exceeded (10 per minute). "
            "Please wait before uploading more images.",
        )

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Unsupported file type '{file.content_type}'. "
            "Only JPEG, PNG, WebP, and GIF images are accepted.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Image must be under 10 MB.")

    _validate_image(image_bytes, file.filename or "unknown")

    # ── Cache check ───────────────────────────────────────────────────────────
    file_hash = hashlib.md5(image_bytes).hexdigest()
    existing = db.query(Garment).filter(Garment.file_hash == file_hash).first()
    if existing:
        log.info("Cache hit for hash %s — returning existing garment %d", file_hash, existing.id)
        result = GarmentOut.model_validate(existing)
        return result.model_copy(update={"from_cache": True})

    ext = Path(file.filename or "upload").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(image_bytes)

    try:
        raw_description, attrs, confidence = await classify_image(image_bytes, file.content_type)
        attrs = normalize_attributes(attrs)
    except anthropic_sdk.AuthenticationError:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            500,
            "ANTHROPIC_API_KEY is invalid or not set. "
            "Add a valid key to your .env file (starts with 'sk-ant-').",
        )
    except anthropic_sdk.APITimeoutError:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            503,
            "AI classification timed out. Please try again in a moment.",
        )
    except anthropic_sdk.RateLimitError:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            429,
            "Anthropic API rate limit exceeded. Please wait before uploading again.",
        )
    except anthropic_sdk.BadRequestError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Image was rejected by the AI API: {exc}") from exc
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(502, f"Classification failed: {exc}") from exc

    garment = Garment(
        filename=filename,
        original_filename=file.filename or filename,
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
        continent=continent.strip(),
        country=country.strip(),
        city=city.strip(),
        designer=designer.strip(),
        file_hash=file_hash,
        confidence=confidence,
        annotations=[],
    )
    db.add(garment)
    db.commit()
    db.refresh(garment)
    return garment


# ── Garments ──────────────────────────────────────────────────────────────────

@app.get("/garments", response_model=List[GarmentOut], tags=["garments"])
def list_garments(
    search: Optional[str] = Query(None, description="Full-text search across descriptions, attributes, and annotations"),
    garment_type: Optional[str] = Query(None),
    style: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    color_palette: Optional[str] = Query(None),
    pattern: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    occasion: Optional[str] = Query(None),
    consumer_profile: Optional[str] = Query(None),
    location_context: Optional[str] = Query(None),
    continent: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    designer: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="4-digit year derived from upload_time"),
    month: Optional[str] = Query(None, description="Zero-padded month, e.g. '03'"),
    trend_keyword: Optional[str] = Query(None, description="Keyword search scoped to trend_notes"),
    db: Session = Depends(get_db),
) -> List[GarmentOut]:
    """List garments with optional full-text search and attribute filters."""
    q = db.query(Garment)

    if search:
        term = f"%{search}%"
        q = q.filter(or_(
            Garment.raw_description.ilike(term),
            Garment.garment_type.ilike(term),
            Garment.style.ilike(term),
            Garment.material.ilike(term),
            Garment.color_palette.ilike(term),
            Garment.pattern.ilike(term),
            Garment.occasion.ilike(term),
            Garment.trend_notes.ilike(term),
            Garment.designer.ilike(term),
            Garment.city.ilike(term),
            cast(Garment.annotations, String).ilike(term),
        ))

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
        "continent": continent,
        "country": country,
        "city": city,
        "designer": designer,
    }
    for field, value in exact_filters.items():
        if value:
            q = q.filter(getattr(Garment, field) == value)

    if year:
        q = q.filter(func.strftime("%Y", Garment.upload_time) == year)
    if month:
        q = q.filter(func.strftime("%m", Garment.upload_time) == month)
    if trend_keyword:
        q = q.filter(Garment.trend_notes.ilike(f"%{trend_keyword}%"))

    return q.order_by(Garment.upload_time.desc()).all()


@app.get("/garments/{garment_id}", response_model=GarmentOut, tags=["garments"])
def get_garment(garment_id: int, db: Session = Depends(get_db)) -> GarmentOut:
    """Fetch a single garment by ID."""
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        raise HTTPException(404, "Garment not found.")
    return garment


@app.get("/garments/{garment_id}/similar", response_model=List[GarmentOut], tags=["garments"])
def get_similar_garments(
    garment_id: int,
    db: Session = Depends(get_db),
) -> List[GarmentOut]:
    """Return up to 4 garments that share at least 2 of: garment_type, style, season.

    Candidates are scored by number of matching attributes and returned highest-score
    first, then newest first. The source garment is always excluded from results.
    """
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        raise HTTPException(404, "Garment not found.")

    # Fetch candidates sharing at least one of the three matching attributes
    from sqlalchemy import or_ as _or
    conditions = []
    if garment.garment_type:
        conditions.append(Garment.garment_type == garment.garment_type)
    if garment.style:
        conditions.append(Garment.style == garment.style)
    if garment.season:
        conditions.append(Garment.season == garment.season)

    if not conditions:
        return []

    candidates = (
        db.query(Garment)
        .filter(Garment.id != garment_id, _or(*conditions))
        .all()
    )

    def _score(g: Garment) -> int:
        return (
            (g.garment_type == garment.garment_type and bool(garment.garment_type))
            + (g.style == garment.style and bool(garment.style))
            + (g.season == garment.season and bool(garment.season))
        )

    similar = [g for g in candidates if _score(g) >= 2]
    similar.sort(key=lambda g: (-_score(g), -(g.id or 0)))
    return similar[:4]


# ── Annotations ───────────────────────────────────────────────────────────────

@app.post("/garments/{garment_id}/annotations", response_model=GarmentOut, tags=["annotations"])
def add_annotation(
    garment_id: int,
    annotation: AnnotationCreate,
    db: Session = Depends(get_db),
) -> GarmentOut:
    """Append a user annotation to a garment."""
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


@app.delete("/garments/{garment_id}/annotations/{index}", response_model=GarmentOut, tags=["annotations"])
def delete_annotation(
    garment_id: int,
    index: int,
    db: Session = Depends(get_db),
) -> GarmentOut:
    """Delete a user annotation by its list index."""
    garment = db.query(Garment).filter(Garment.id == garment_id).first()
    if not garment:
        raise HTTPException(404, "Garment not found.")

    annotations = list(garment.annotations or [])
    if index < 0 or index >= len(annotations):
        raise HTTPException(400, f"Annotation index {index} is out of range.")

    garment.annotations = [a for i, a in enumerate(annotations) if i != index]
    flag_modified(garment, "annotations")
    db.commit()
    db.refresh(garment)
    return garment


# ── Filters ───────────────────────────────────────────────────────────────────

@app.get("/filters", response_model=FilterOptions, tags=["filters"])
def get_filters(db: Session = Depends(get_db)) -> FilterOptions:
    """Return all distinct attribute values currently in the database.

    Filter options are fully data-driven — they reflect exactly what has
    been uploaded and classified, with no hardcoded values.
    """
    def distinct(col) -> list[str]:
        return sorted({v for (v,) in db.query(col).distinct().all() if v})

    def distinct_expr(expr) -> list[str]:
        return sorted({r[0] for r in db.query(expr).distinct().all() if r[0]})

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
        continent=distinct(Garment.continent),
        country=distinct(Garment.country),
        city=distinct(Garment.city),
        designer=distinct(Garment.designer),
        year=sorted(
            distinct_expr(func.strftime("%Y", Garment.upload_time)), reverse=True
        ),
        month=distinct_expr(func.strftime("%m", Garment.upload_time)),
    )


# ── Images ────────────────────────────────────────────────────────────────────

@app.get("/images/{filename}", tags=["images"])
def serve_image(filename: str) -> FileResponse:
    """Serve an uploaded image file.  Path traversal is prevented by taking only the basename."""
    safe = Path(filename).name
    file_path = UPLOAD_DIR / safe
    if not file_path.exists():
        raise HTTPException(404, "Image not found.")
    return FileResponse(file_path)
