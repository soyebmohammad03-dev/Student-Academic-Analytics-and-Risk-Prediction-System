# Architecture

```
 ┌──────────────┐   offline    ┌───────────────────────┐   artifacts   ┌──────────┐
 │  data/raw    │ ───────────▶ │  backend/analytics    │ ────────────▶ │ models/  │
 │  (UCI CSVs)  │              │  stats · EDA · prep · │               │ (.joblib │
 └──────────────┘              │  training · evaluation│               │ + meta)  │
                               └──────────┬────────────┘               └────┬─────┘
                                          │ imported by                     │ loaded by
                                          ▼                                 ▼
                               ┌──────────────────────────────────────────────────┐
                               │  backend/app  (FastAPI)                          │
                               │  routes → services → analytics / model registry  │
                               └──────────────────────┬───────────────────────────┘
                                                      │ JSON over HTTP (/api/v1)
                                                      ▼
                               ┌──────────────────────────────────────────────────┐
                               │  frontend  (Next.js · TypeScript · Tailwind)     │
                               └──────────────────────────────────────────────────┘
```

## Principles

- **Training is separate from inference.** Models are trained offline by scripts in
  the analytics package and persisted with metadata. The API never trains.
- **One-way dependencies.** `app` → `analytics`; `analytics` never imports `app`.
  The frontend only talks to the API.
- **Honest UI.** The frontend renders only data returned by the API. Module status is
  declared by the backend (`GET /api/v1/project`), so unfinished modules are shown as
  planned rather than with placeholder numbers.
- **Reproducibility.** Fixed seeds, pipeline objects that bundle preprocessing with the
  model, and versioned metadata alongside every artifact.

## Backend layout

| Path                    | Responsibility                                  |
| ----------------------- | ----------------------------------------------- |
| `app/main.py`           | App factory, CORS, router registration          |
| `app/core/config.py`    | `pydantic-settings` configuration (`SAARPS_*` env vars) |
| `app/api/routes/`       | One module per resource                         |
| `app/schemas/`          | Pydantic response/request models                |
| `app/services/`         | Orchestration between routes and analytics      |
| `app/api/errors.py`     | Consistent `{code, detail}` error bodies        |
| `analytics/data/`       | Dataset acquisition, loading, validation, dictionary, cohort overlap |
| `analytics/` (other)    | Statistics, EDA, preprocessing, modelling (Phase 3+) |

## Data layer (Phase 2)

```
UCI archive ──download.py──▶ data/raw/*.csv ──loader.py──▶ LoadedCohort(raw, typed)
 (nested zip,  checksum-        (git-ignored)                    │
  fetched once) verified                                         ├─▶ validation.py ─▶ ValidationReport
                                                                 └─▶ overlap.py    ─▶ OverlapReport
                                dictionary.py  (single source of column metadata)
                                    ├─▶ validation rules
                                    ├─▶ GET /dataset/schema
                                    └─▶ docs/DATA_DICTIONARY.md (docgen.py; a test keeps it in sync)
```

- **Acquisition** is an explicit command (`python -m analytics.data.download`), never a
  side effect of starting the API.
- **Loading** reads every cell as text first, then builds a typed frame (`Int64` for
  numerical columns, `string` for categorical). Unparsable values become missing in
  the typed frame and are counted as *invalid* by validation, so nothing is lost silently.
- **Validation** only reports. It returns structured checks (`pass` / `warning` / `fail`),
  per-column profiles and factual observations. It never drops rows.
- **Caching.** `app/services/dataset.py` holds a `DatasetStore` that loads and validates
  each cohort once and serves later requests from memory. The cache key includes the
  file's modification time and size, so a re-download is picked up without a restart.

## Frontend layout

| Path                     | Responsibility                                  |
| ------------------------ | ----------------------------------------------- |
| `src/app/`               | App Router pages, one folder per module         |
| `src/components/layout/` | Shell: sidebar, top bar, page header            |
| `src/components/ui/`     | Design-system primitives                        |
| `src/components/data-explorer/` | Data Explorer: overview, quality, records table, dictionary, overlap |
| `src/lib/`               | Module registry, typed API client, `useApi` fetch hook |
| `src/app/globals.css`    | Design tokens (colour, type, radius, elevation) for light and dark themes |

## API (current)

All paths are under `/api/v1`. `cohort` is required where listed and must be `math`
or `portuguese`.

| Method | Path               | Parameters | Description |
| ------ | ------------------ | ---------- | ----------- |
| GET    | `/health`          | — | Liveness, version and environment |
| GET    | `/project`         | — | Project identity, dataset presence, module status |
| GET    | `/dataset/summary` | `cohort` | Rows, columns, numerical/categorical counts, missing/duplicate/invalid counts, validation status, source, target |
| GET    | `/dataset/schema`  | `cohort` | Data dictionary for all 33 columns plus values observed in the cohort |
| GET    | `/dataset/quality` | `cohort` | Validation checks, observations, columns with issues |
| GET    | `/dataset/records` | `cohort`, `page` (≥1), `page_size` (1–100, default 25), `search` (≤100 chars) | Paginated raw records; `row` is the 1-based file position, not an ID |
| GET    | `/dataset/overlap` | — | Approximate cross-cohort matching with its assumptions |

Errors use one shape, `{"code": "...", "detail": "..."}`:

| Status | `code` | When |
| ------ | ------ | ---- |
| 422 | `invalid_request` | Unknown cohort, missing cohort, page or page size out of range, search too long |
| 503 | `dataset_unavailable` | Dataset files not downloaded; `detail` gives the command |
