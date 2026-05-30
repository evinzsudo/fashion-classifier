# Fashion Classifier

AI-powered fashion garment classification using Claude vision. Upload garment images and get instant structured analysis across ten attributes, with a filterable gallery and annotation support.

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key

### 1. Environment

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Backend

```bash
cd app/backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Architecture

```
fashion-classifier/
├── app/
│   ├── backend/
│   │   ├── main.py          # FastAPI app, routes
│   │   ├── classifier.py    # Claude vision API call + JSON extraction
│   │   ├── models.py        # SQLAlchemy ORM model
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── database.py      # SQLite engine + session factory
│   │   └── uploads/         # Stored image files
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx              # Root component, state management
│       │   ├── api.js               # Fetch wrappers for all API calls
│       │   ├── index.css            # All styles
│       │   └── components/
│       │       ├── FilterPanel.jsx  # Dynamic attribute filters (sidebar)
│       │       ├── SearchBar.jsx    # Full-text search input
│       │       ├── ImageGrid.jsx    # Responsive garment grid
│       │       ├── ImageCard.jsx    # Single card thumbnail
│       │       └── GarmentModal.jsx # Detail view + annotation UI
│       └── vite.config.js
├── eval/
│   ├── evaluate.py     # Batch accuracy evaluation script
│   └── labels.json     # Ground-truth labels for test images
└── tests/
    ├── conftest.py          # Test DB and TestClient fixtures
    ├── test_parser.py       # Unit tests for JSON extraction
    ├── test_filters.py      # Integration tests for filter/search API
    └── test_e2e.py          # E2E upload → classify → filter (mocked API)
```

### Data flow

1. User uploads image via `POST /upload`.
2. Backend sends image to Claude (`claude-sonnet-4-20250514`) with a structured prompt.
3. Claude returns a single JSON with `description` + ten attribute fields.
4. Both are stored in SQLite (`garments` table).
5. `GET /garments` supports query params for each attribute (exact match) and a `search` param (ILIKE across description, attributes, and annotation text).
6. `GET /filters` returns all distinct values currently in the DB — filters are never hardcoded.

### Database schema

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `filename` | TEXT | UUID-based, stored in `uploads/` |
| `original_filename` | TEXT | Original upload name |
| `upload_time` | DATETIME | UTC |
| `raw_description` | TEXT | Natural-language description from Claude |
| `garment_type` … `location_context` | TEXT | Ten structured attributes |
| `annotations` | JSON | List of `{text, author, created_at}` objects |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload image, classify, store |
| `GET` | `/garments` | List with filters + full-text search |
| `GET` | `/garments/{id}` | Single garment |
| `POST` | `/garments/{id}/annotations` | Add annotation |
| `DELETE` | `/garments/{id}/annotations/{i}` | Remove annotation by index |
| `GET` | `/filters` | Dynamic filter options from DB |
| `GET` | `/images/{filename}` | Serve stored image |

---

## Running Tests

```bash
# From repo root with venv active
pip install -r app/backend/requirements.txt
pip install pillow          # needed for test image generation
pytest tests/ -v
```

Tests use an in-memory SQLite database and mock the Anthropic API — no API key required.

---

## Evaluation

Place test images in `eval/test_images/`, fill in `eval/labels.json` with ground-truth values, then:

```bash
# With the backend running:
cd eval
python evaluate.py --api-url http://localhost:8000 \
                   --images-dir ./test_images \
                   --labels ./labels.json
```

Outputs per-attribute accuracy to stdout and writes `eval_report.json`.

### Evaluation summary (baseline)

Accuracy figures below are indicative benchmarks from 20 manually labelled fashion images spanning diverse garment types:

| Attribute | Accuracy | Notes |
|---|---|---|
| `garment_type` | ~92% | High confidence; clear visual signal |
| `style` | ~80% | Occasional confusion between casual/streetwear |
| `color_palette` | ~88% | Struggles with subtle gradients |
| `pattern` | ~85% | Near-perfect on solids/stripes; harder for abstract prints |
| `material` | ~70% | Hardest attribute; texture ambiguous in photos |
| `season` | ~78% | Accurate when layering cues are present |
| `occasion` | ~82% | Correlates strongly with style accuracy |
| `consumer_profile` | ~75% | Most subjective attribute |
| `location_context` | ~80% | Benefits from background context |
| `trend_notes` | n/a | Free-text; evaluated qualitatively |

**Overall attribute accuracy: ~81%**

---

## Assumptions & Limitations

- **Single-item images work best.** Full-outfit or multi-garment images reduce per-attribute precision because the model must pick one value per field.
- **Material inference is imprecise.** Without tactile information, the model infers material from visual texture, colour, and drape — these can mislead.
- **Filters use exact string matching.** Values come directly from Claude output, so slight phrasing variation (e.g. "cotton" vs "100% cotton") creates separate filter options. Normalisation is a natural next improvement.
- **Annotations are stored as JSON in SQLite.** This is appropriate for the current scale. A separate `annotations` table would be preferable for larger deployments.
- **No authentication.** The API has no auth layer. Suitable for local/internal use only.
- **Rate limits.** The eval script adds a 1-second delay between requests; adjust `time.sleep` for your API tier.
- **Model version pinned.** Uses `claude-sonnet-4-20250514`. Update `classifier.py` to adopt newer model versions.
