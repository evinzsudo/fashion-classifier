PYTHON   := python3
PIP      := pip3
UVICORN  := $(PYTHON) -m uvicorn
NPM      := npm

.PHONY: install install-backend install-frontend
.PHONY: run-backend run-frontend
.PHONY: test eval eval-dry-run
.PHONY: download-images clean help

# ── Install ───────────────────────────────────────────────────────────────────

install: install-backend install-frontend

install-backend:
	$(PIP) install -r app/backend/requirements.txt

install-frontend:
	cd app/frontend && $(NPM) install

# ── Run ───────────────────────────────────────────────────────────────────────
# Run each target in a separate terminal.

run-backend:
	$(UVICORN) app.backend.main:app --reload --port 8000

run-frontend:
	cd app/frontend && $(NPM) run dev

# ── Test ──────────────────────────────────────────────────────────────────────

test:
	$(PYTHON) -m pytest tests/ -v

# ── Eval ──────────────────────────────────────────────────────────────────────
# Requires a running backend (make run-backend) and images in eval/test_images/.

eval:
	$(PYTHON) eval/evaluate.py \
		--api-url http://localhost:8000 \
		--images-dir eval/test_images \
		--labels eval/labels.json

# Classify directly without uploading to the backend (no DB writes).
eval-dry-run:
	$(PYTHON) eval/evaluate.py \
		--images-dir eval/test_images \
		--labels eval/labels.json \
		--dry-run

download-images:
	$(PYTHON) eval/download_test_images.py --per-term 5

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -not -path '*/node_modules/*' -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -not -path '*/node_modules/*' -delete 2>/dev/null || true
	rm -f fashion.db test_fashion.db

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make install         Install all Python and Node dependencies"
	@echo "  make run-backend     Start FastAPI on http://localhost:8000"
	@echo "  make run-frontend    Start React dev server on http://localhost:5173"
	@echo "  make test            Run 35 pytest tests (no API key needed)"
	@echo "  make eval            Evaluate accuracy against labelled test images"
	@echo "  make eval-dry-run    Same, but classify directly — no DB writes"
	@echo "  make download-images Download 50 test images from Pexels"
	@echo "  make clean           Remove __pycache__, .pyc, and local DBs"
	@echo ""
