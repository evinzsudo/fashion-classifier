# Fashion Classifier

AI-powered fashion garment classification using Claude vision. Upload garment images and get instant structured analysis across ten attributes, with a filterable gallery and annotation support.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Quick Start](#2-quick-start)
3. [Architecture Overview](#3-architecture-overview)
4. [AI Classification Design](#4-ai-classification-design)
5. [Evaluation Results](#5-evaluation-results)
6. [Product Decisions & Trade-offs](#6-product-decisions--trade-offs)
7. [Known Limitations & Next Steps](#7-known-limitations--next-steps)
8. [How to Get API Keys](#8-how-to-get-api-keys)
9. [Running Tests & Evaluation](#9-running-tests--evaluation)
10. [API Reference](#10-api-reference)
11. [Deployment](#11-deployment)
12. [Next Steps](#12-next-steps)

---

## 1. Project Overview

Fashion Classifier is an AI-powered web application that helps fashion designers organize, search, and reuse garment inspiration imagery. Upload a photo of any garment and receive instant AI-driven classification across ten structured attributes — garment type, style, material, color palette, pattern, season, occasion, consumer profile, trend notes, and location context. Filter and annotate your growing collection to build a personal, searchable inspiration library.

---

## 2. Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+, an Anthropic API key.

**Step 1 — Configure environment**

```bash
cp .env.example .env
# Open .env and set your ANTHROPIC_API_KEY
# Optionally set PEXELS_API_KEY for test-image downloads
```

Get your Anthropic API key at [console.anthropic.com](https://console.anthropic.com) → API Keys → Create key.
Get a free Pexels API key at [pexels.com/api](https://www.pexels.com/api/) (200 requests/hour on the free tier).

**Step 2 — Install dependencies**

```bash
make install
```

**Step 3 — Run the app**

Open two terminals:

```bash
# Terminal 1 — backend (http://localhost:8000)
make run-backend

# Terminal 2 — frontend (http://localhost:5173)
make run-frontend
```

Then open **http://localhost:5173** in your browser.

Interactive API docs are available at **http://localhost:8000/docs**.

---

## 3. Architecture Overview

The application is composed of four layers:

- **FastAPI backend** — handles file upload, invokes the Claude vision API, normalizes attribute values, and persists results to SQLite via SQLAlchemy ORM.
- **React frontend** — a Vite-bundled single-page app with a dynamic filter sidebar, responsive image grid, full-text search, and an annotation modal.
- **SQLite database** — stores garment records (attributes, descriptions, annotations, upload metadata) in a single file (`fashion.db`). Zero configuration for local deployment.
- **Claude Vision API** — `claude-sonnet-4-20250514` classifies each uploaded image, returning a structured JSON with a natural-language description and all ten attribute fields in a single API call.

### Data Flow

```
User selects image + optional metadata (location, designer)
          │
          ▼
  POST /upload  (multipart form)
          │
          ▼
  Backend saves file to uploads/ with UUID filename
          │
          ▼
  Image encoded to base64 → sent to Claude API
  (claude-sonnet-4-20250514, single call)
          │
          ▼
  Claude returns JSON:
    { description, garment_type, style, material,
      color_palette, pattern, season, occasion,
      consumer_profile, trend_notes, location_context }
          │
          ▼
  Normalization pass (normalizer.py)
  collapses near-duplicate attribute values
          │
          ▼
  Record stored in SQLite (garments table)
          │
          ▼
  React fetches GET /garments + GET /filters
          │
          ▼
  Filter sidebar + image grid rendered in browser
```

### Directory Structure

```
/app/backend/   FastAPI routes, classifier, normalizer, DB models
/app/frontend/  React + Vite, component-based UI
/eval/          Evaluation script + test images + labels
/tests/         45 pytest tests (unit, integration, e2e)
Makefile        make install / run / test / eval
```

Detailed layout:

```
fashion-classifier/
├── app/
│   ├── backend/
│   │   ├── main.py          # FastAPI app and all routes
│   │   ├── classifier.py    # Claude API call + JSON extraction + regex fallback
│   │   ├── normalizer.py    # Attribute normalization rules
│   │   ├── models.py        # SQLAlchemy ORM model (Garment)
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── database.py      # SQLite engine + session factory
│   │   └── uploads/         # Stored image files (UUID-named)
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx              # Root component, global state
│       │   ├── api.js               # Fetch wrappers for all API endpoints
│       │   ├── index.css            # All styles
│       │   └── components/
│       │       ├── FilterPanel.jsx  # Dynamic attribute filter sidebar
│       │       ├── SearchBar.jsx    # Full-text search input
│       │       ├── ImageGrid.jsx    # Responsive garment card grid
│       │       ├── ImageCard.jsx    # Single garment thumbnail + preview
│       │       └── GarmentModal.jsx # Detail view + annotation UI
│       └── vite.config.js
├── eval/
│   ├── evaluate.py              # Batch accuracy evaluation script
│   ├── download_test_images.py  # Pexels image downloader
│   ├── test_images/             # Images used for evaluation
│   └── labels.json              # Ground-truth labels for test images
├── tests/
│   ├── conftest.py          # In-memory DB and TestClient fixtures
│   ├── test_parser.py       # Unit tests for JSON extraction logic
│   ├── test_filters.py      # Integration tests for filter/search API
│   └── test_e2e.py          # E2E upload → classify → filter (Claude mocked)
├── .env.example
├── Makefile
└── pytest.ini
```

---

## 4. AI Classification Design

### Single API Call

Each image upload triggers exactly one Claude API call. That call returns a JSON object containing both a natural-language `description` and all ten structured attribute fields simultaneously:

```
garment_type, style, material, color_palette, pattern,
season, occasion, consumer_profile, trend_notes, location_context
```

Combining description and structured output in one call halves latency compared to making two separate requests. The trade-off is that a malformed JSON response loses both — this is mitigated by a regex fallback (see below).

### Model Choice

The app uses **`claude-sonnet-4-20250514`**, which provides strong vision understanding and reliable structured JSON output. The model version is pinned in `classifier.py` to ensure reproducible behavior; update it there to adopt future model versions.

### Prompt Engineering

The prompt passed to Claude includes:

- An explicit JSON schema showing the expected field names and value types, so the model produces machine-parseable output without guessing the format.
- An explicit instruction not to wrap the JSON in markdown fences (` ```json ` blocks), since the response is parsed directly.
- **Constrained vocabularies** for two high-variance fields: `style` is restricted to 10 values (`casual`, `formal`, `minimalist`, `bohemian`, `athletic`, `streetwear`, `vintage`, `preppy`, `romantic`, `avant-garde`) and `color_palette` to 8 values (`neutral earth tones`, `bold primary colors`, `pastels`, `monochrome`, `warm tones`, `cool tones`, `black and white`, `mixed`). Constraints collapse the open-ended output space, reducing filter clutter and improving cross-garment comparability.
- **Three few-shot examples** (a floral dress, a structured blazer, and distressed jeans) demonstrating ideal JSON output, which anchors Claude's interpretation of each field in fashion-domain terms and improves consistency across diverse image types.
- A **`confidence` object** alongside the attribute fields, where each attribute has a 0.0–1.0 self-reported confidence score. Scores below 0.7 are surfaced in the UI as gray italic text with the percentage shown, signalling attributes the model is less certain about.

### Fallback Extraction

If Claude's response contains stray text around the JSON (e.g., a preamble sentence), `extract_json` in `classifier.py` applies a regex to find the outermost `{...}` block and parses that. This handles edge cases where the model ignores the "no markdown" instruction. If extraction fails entirely, the upload returns a 422 error with the raw Claude response included for debugging.

### Attribute Normalization

After classification, `normalizer.py` applies a normalization pass before any value is written to the database. This step:

- Collapses near-duplicate phrasings to a single canonical form, e.g., `"cotton blend and polyester"` → `"cotton blend"`, `"sweaters"` → `"sweater"`, `"blazer and skirt set"` → `"blazer"`.
- Uses priority-ordered regex rules applied most-specific first, so a more precise rule always takes precedence over a broader one.
- Is intentionally conservative — only values it can identify with high confidence are collapsed; ambiguous cases pass through unchanged.

Normalization keeps filter options clean and manageable. Without it, every phrasing variation Claude produces becomes a separate checkbox in the filter sidebar.

### Dual Location Tracking

Location is tracked as two independent data sources:

| Field | Source | Example values |
|---|---|---|
| `location_context` | AI-inferred from image | `"urban"`, `"beachside"`, `"office"` |
| `continent` / `country` / `city` | User-supplied at upload | `"Europe"`, `"France"`, `"Paris"` |

Claude can reliably infer a descriptive environmental context from visual cues in the image background, but cannot reliably identify actual geography. User-supplied fields capture the true geographic origin when the designer knows it, without forcing it on every upload.

---

## 5. Evaluation Results

Evaluation was run against 50 manually labelled test images spanning diverse garment types, styles, and contexts. The evaluation script (`eval/evaluate.py`) uploads each image to the running backend and compares Claude's classified attributes against ground-truth labels in `eval/labels.json`.

**Matching logic:** partial-match is used rather than strict exact-match. For example, a predicted value of `"cotton blend"` is counted as correct when the ground-truth label is `"cotton"`, because fashion terminology naturally overlaps. Strict exact-match would systematically under-count correct answers given how varied garment descriptions are in practice.

| Attribute | Accuracy | Notes |
|---|---|---|
| garment_type | 72% | Strong visual signal; compound descriptions reduce accuracy |
| season | 74% | Accurate when layering or fabric weight is visible |
| occasion | 56% | Overlap between "casual everyday" and "business casual" |
| color_palette | 68% | Struggles with subtle gradients and mixed palettes |
| pattern | 71% | Near-perfect on solids/stripes; hard for abstract prints |
| material | 36% | Hardest: tactile properties invisible in photos |
| style | 24% | Most subjective attribute; cultural context dependent |
| consumer_profile | 58% | Correlates with style; suffers from same subjectivity |
| location_context | 65% | Improves when background is visible |
| **Overall** | **52.4%** | Across all 50 test images × 9 attributes |

`garment_type` and `season` perform best because they carry strong, unambiguous visual signals — a coat is recognizably a coat, and heavy layering is a clear seasonal cue. `material` (36%) and `style` (24%) are the hardest attributes: material requires tactile information that is simply invisible in a photograph, and style is a culturally loaded judgment that varies significantly across designers and markets. Accuracy across all attributes could be improved by providing richer context in the upload form, using images with better lighting and unobstructed garment visibility, and refining prompts with domain-specific few-shot examples drawn from real designer workflows.

---

## 6. Product Decisions & Trade-offs

**SQLite vs PostgreSQL**

SQLite was chosen for zero-configuration local deployment — no database server to install, configure, or maintain. The entire database is a single file (`fashion.db`). The trade-off is that SQLite does not support concurrent writes, making it unsuitable for multi-user or cloud deployments. Migrating to PostgreSQL requires only changing the SQLAlchemy connection string and installing `psycopg2`.

**User-supplied vs AI-inferred location**

The AI can reliably infer descriptive context ("urban", "beach", "office") from the image, but cannot reliably identify actual geographic location. User-supplied `continent`, `country`, and `city` fields capture true geography when the designer has it. Both sources are independently filterable in the sidebar. Upload fields are optional so they never block the core workflow.

**Partial-match evaluation logic**

Using partial-match instead of exact-match in `evaluate.py` reflects how fashion terminology actually works: `"cotton blend"` is a correct answer when the ground truth is `"cotton"` because the prediction is more specific, not wrong. Strict exact-match would systematically penalize Claude for being more precise than the label. Both modes are available by adjusting the `strict` flag in the evaluation script.

**Attribute normalization**

Normalization is applied before storage, not at query time. This means filter values in the database are already canonical — `GET /filters` returns clean options without any post-processing. The trade-off is that the original Claude output is not stored, so it is not possible to see what phrasing the model originally used (only the normalized value is visible). Given that the goal is clean filter UX, normalization-before-storage is the right call at this scale.

**Single API call**

Combining the natural-language description and all ten structured attributes in one Claude call keeps classification logic in a single function (`classifier.py`) and halves per-upload latency compared to two separate calls. The downside is that a single malformed JSON response loses both description and attributes simultaneously. The regex fallback in `extract_json` handles the most common failure modes. For a higher-reliability production system, storing the raw Claude response and re-parsing asynchronously would be a sensible addition.

---

## 7. Known Limitations & Next Steps

**Structured tags**

Annotations are currently free-text with an author name. A proper tag system with predefined (or user-defined) labels would make annotations filterable as their own independent dimension and dramatically improve searchability of annotated garments.

**Eval DB isolation**

`evaluate.py` uploads test images to the running backend, inserting real rows into the live database. Running the evaluation multiple times creates duplicate records. Use the `--dry-run` flag to classify images without storing results, or point `--api-url` at a separate backend instance backed by a temporary database.

**No authentication**

The API has no auth layer. All endpoints are publicly accessible to anyone who can reach the server. This is appropriate for local or single-user deployment only. Adding authentication would require token-based auth middleware and user-scoped data isolation.

**Cloud deployment**

A cloud deployment would require: object storage (e.g., AWS S3 or GCS) to replace the local `uploads/` folder, PostgreSQL to replace SQLite, proper secret management (e.g., AWS Secrets Manager or environment injection) for the Anthropic API key, and a reverse proxy (nginx or a load balancer) in front of the FastAPI process.

---

## 8. How to Get API Keys

**Anthropic API key** (required)

1. Sign up or log in at [console.anthropic.com](https://console.anthropic.com).
2. Navigate to **API Keys** in the left sidebar.
3. Click **Create Key**, give it a name, and copy the key value (it is shown only once).
4. Add it to your `.env` file as `ANTHROPIC_API_KEY=sk-ant-...`.

**Pexels API key** (optional — only needed to download test images)

1. Sign up for a free account at [pexels.com/api](https://www.pexels.com/api/).
2. Your API key appears on the dashboard immediately after sign-up.
3. The free tier includes 200 requests per hour, which is sufficient for downloading a test image set.
4. Add it to your `.env` file as `PEXELS_API_KEY=...`.

---

## 9. Running Tests & Evaluation

### Tests

Tests use an in-memory SQLite database and mock the Anthropic API. No API key is required to run them.

```bash
# Run all 45 tests
make test

# Or run directly with pytest for verbose output
pytest tests/ -v
```

The test suite covers:

- **Unit tests** (`test_parser.py`) — JSON extraction and regex fallback logic in `classifier.py`.
- **Integration tests** (`test_filters.py`) — filter and search API endpoints against a seeded in-memory database.
- **E2E tests** (`test_e2e.py`) — full upload → classify → filter flow with the Claude API mocked.

### Evaluation

The evaluation script requires a running backend and a valid `ANTHROPIC_API_KEY`. It uploads each image in `eval/test_images/` to the backend, classifies it, and compares results to ground-truth labels in `eval/labels.json`.

```bash
# Evaluation (requires running backend + ANTHROPIC_API_KEY)
make run-backend   # terminal 1
make eval          # terminal 2

# Dry-run evaluation (no running backend needed, no DB writes)
make eval-dry-run

# Download test images (requires PEXELS_API_KEY)
python eval/download_test_images.py --per-term 5
```

The script prints per-attribute accuracy to stdout and writes a full `eval_report.json` alongside the script. Use `--dry-run` to run classification through the Claude API directly without inserting any rows into the database — useful for benchmarking prompt changes without polluting the garment collection.

---

## 10. API Reference

FastAPI auto-generates interactive API docs (with a built-in try-it UI) at **http://localhost:8000/docs** when the backend is running. The examples below use `curl` against a locally running server.

### GET /health

Check server liveness and API key status.

```bash
curl http://localhost:8000/health
# {"status":"ok","anthropic_api_key":"configured","version":"1.0.0"}
```

### POST /upload

Upload a garment image and classify it with Claude. All form fields except `file` are optional metadata.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/jacket.jpg" \
  -F "designer=Acne Studios" \
  -F "continent=Europe" \
  -F "country=Sweden" \
  -F "city=Stockholm"
```

If the same image has been uploaded before (identical MD5 hash), the existing result is returned immediately with `"from_cache": true` — no Claude API call is made.

### GET /garments

List all garments, with optional full-text search and attribute filters. All parameters are optional and combinable.

```bash
# All garments
curl "http://localhost:8000/garments"

# Filter by garment type and style
curl "http://localhost:8000/garments?garment_type=dress&style=romantic"

# Full-text search across descriptions, attributes, and annotations
curl "http://localhost:8000/garments?search=oversized+denim"

# Filter by location and designer
curl "http://localhost:8000/garments?continent=Asia&designer=Issey+Miyake"

# Filter by upload year/month
curl "http://localhost:8000/garments?year=2025&month=03"

# Keyword search scoped to trend notes
curl "http://localhost:8000/garments?trend_keyword=Y2K"
```

### GET /garments/{id}

Fetch a single garment by its integer ID.

```bash
curl http://localhost:8000/garments/42
```

### GET /garments/{id}/similar

Return up to 4 garments that share at least 2 of the three attributes: `garment_type`, `style`, `season`. Results are sorted by number of matching attributes (most similar first).

```bash
curl http://localhost:8000/garments/42/similar
```

### POST /garments/{id}/annotations

Append a user annotation (text note) to a garment.

```bash
curl -X POST http://localhost:8000/garments/42/annotations \
  -H "Content-Type: application/json" \
  -d '{"text": "Spotted at Paris Fashion Week AW25", "author": "editor"}'
```

### DELETE /garments/{id}/annotations/{index}

Delete an annotation by its 0-based index in the garment's annotation list.

```bash
curl -X DELETE http://localhost:8000/garments/42/annotations/0
```

### GET /filters

Return all distinct attribute values currently present in the database. Used to populate the filter sidebar. Values are fully data-driven — they reflect exactly what has been uploaded.

```bash
curl http://localhost:8000/filters
# {"garment_type":["blazer","dress","hoodie"],"style":["casual","formal"],...}
```

---

## 11. Deployment

> **Note:** For this POC, local deployment is intentional. Running locally keeps setup to a single `make install && make run-backend && make run-frontend`, avoids cloud costs, and removes the need to configure object storage, managed databases, or secret managers. The steps below describe a straightforward path to a hosted deployment when that becomes necessary.

### Backend — Railway or Render (free tier)

Both platforms can serve a FastAPI app from a GitHub repo with minimal configuration. The steps below use Railway as an example; Render is nearly identical.

1. Push the repo to GitHub (if not already there).
2. Create a new project at [railway.app](https://railway.app) and select **Deploy from GitHub repo**.
3. Point Railway at the repo root and set the **start command** to:
   ```
   uvicorn app.backend.main:app --host 0.0.0.0 --port $PORT
   ```
4. Set the following environment variables in the Railway dashboard under **Variables**:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   CORS_ORIGINS=https://your-frontend.vercel.app
   DATABASE_URL=postgresql://user:pass@host:5432/dbname   # see Database section
   ```
5. Railway assigns a public URL such as `https://fashion-classifier.up.railway.app`. Copy this — you will need it when deploying the frontend.

### Frontend — Vercel or Netlify

1. Create a new project at [vercel.com](https://vercel.com) and import the same GitHub repo.
2. Set the **root directory** to `app/frontend` and the **build command** to `npm run build` with output directory `dist`.
3. Add an environment variable:
   ```
   VITE_API_URL=https://fashion-classifier.up.railway.app
   ```
4. Update `app/frontend/src/api.js` to read the base URL from the environment variable:
   ```js
   const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
   ```
5. Vercel deploys automatically on every push to `main` and provides a public URL.

### Database — SQLite to PostgreSQL

SQLite is fine for a single-user local prototype but does not support concurrent writes and stores data in a local file that is lost when a cloud container restarts.

For a production deployment, swap to **PostgreSQL**. [Supabase](https://supabase.com) provides a free hosted PostgreSQL instance.

**What to change:**

1. Add `psycopg2-binary` to `requirements.txt`.
2. In `app/backend/database.py`, replace the SQLite connection string:
   ```python
   # Before (SQLite)
   SQLALCHEMY_DATABASE_URL = "sqlite:///./fashion.db"

   # After (PostgreSQL via env var)
   import os
   SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]
   ```
3. Remove the `connect_args={"check_same_thread": False}` kwarg — that flag is SQLite-specific.
4. Run `alembic upgrade head` (or recreate the schema) against the new database on first deploy.

The SQLAlchemy ORM code in `models.py` and all query logic in `main.py` are already database-agnostic and require no changes.

### Environment variables in production

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude vision classification |
| `DATABASE_URL` | Yes (cloud) | PostgreSQL connection string; SQLite path for local |
| `CORS_ORIGINS` | Yes (cloud) | Comma-separated list of allowed frontend origins, e.g. `https://your-app.vercel.app` |
| `VITE_API_URL` | Frontend | Public backend URL; consumed at build time by Vite |

For local development these are set in `.env`. On Railway/Render/Vercel they are set through each platform's environment variable UI and injected at runtime — never commit the actual values to the repo.

---

## 12. Next Steps

The following improvements would be the highest-value additions with more development time, roughly in priority order:

1. **Structured tagging system** — Replace free-text annotations with a tags table (many-to-many between `tags` and `garments`). Tags would be predefined or user-created, stored as normalized strings, and exposed as their own filter dimension in the sidebar. This makes annotated garments fully searchable without relying on string matching inside JSON blobs.

2. **Eval database isolation** — The evaluation script currently writes real rows into the live database. The `--dry-run` flag already avoids this, but a cleaner solution is a separate test database (controlled via `--db-url`) that is created, populated, and torn down as part of the eval run. This would let the eval CI job run safely against a production-like backend without polluting the garment collection.

3. **Real-time collaborative annotations** — Replace the current polling-based annotation UI with a WebSocket channel (FastAPI natively supports `websockets`). Multiple designers could annotate the same garment simultaneously and see each other's notes appear live, which is the primary workflow for a shared trend-research tool.

4. **Batch image processing with async queue** — The current upload endpoint is synchronous: one HTTP request, one Claude API call, one response. For bulk uploads (the existing `/bulk-upload` endpoint queues files sequentially), a proper async task queue (Celery + Redis, or FastAPI `BackgroundTasks` for lighter workloads) would let users upload many images at once and poll for results, rather than waiting on a long HTTP request.

5. **Prompt optimization based on eval results** — `style` accuracy is 24% and `material` is 36%. Both could be improved with targeted prompt changes: domain-specific few-shot examples for `style` drawn from real designer vocabulary, and explicit instructions for `material` to infer from texture and sheen cues rather than tactile assumption. Running eval as a regression gate in CI would prevent prompt regressions as the prompt evolves.

6. **User authentication** — Add token-based auth (JWT via `python-jose`, or OAuth via `authlib`) with user-scoped data isolation. Each designer's garment library would be private by default, with optional sharing. This is a prerequisite for any multi-user or cloud-hosted deployment.

7. **Export functionality** — Allow designers to export their collection as a CSV (all attributes as columns) or as a PDF mood board (grid of thumbnails with key attributes). Both are straightforward given the existing structured data — `pandas` + `reportlab` for PDF, or a client-side React-to-PDF library like `react-pdf`.
