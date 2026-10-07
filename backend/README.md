# Backend

FastAPI service and offline analytics pipeline for the
**Student Academic Analytics and Risk Prediction System**.

```
backend/
├── app/              # Web layer (FastAPI)
│   ├── main.py       # Application factory and entry point
│   ├── core/         # Settings / environment handling
│   ├── api/          # Routers and route modules
│   ├── schemas/      # Pydantic request/response models
│   └── services/     # Adapters between routes and the analytics package
├── analytics/
│   └── data/         # Download, loading, validation, data dictionary, cohort overlap
└── tests/
```

`analytics` never imports from `app`. Training happens offline and writes artifacts
to `../models/`; the API only loads those artifacts for inference.

## Setup

```bash
cd backend
uv venv --python 3.12 .venv     # or: python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"      # or: pip install -e ".[dev]"
cp .env.example .env   # optional
python -m analytics.data.download   # download + verify the UCI dataset into ../data/raw
```

Re-generate the data dictionary document after changing `analytics/data/dictionary.py`:

```bash
python -m analytics.data.docgen
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/api/v1/health
- Interactive docs: http://localhost:8000/docs

## Test and lint

```bash
pytest
ruff check .
ruff format --check .
```
