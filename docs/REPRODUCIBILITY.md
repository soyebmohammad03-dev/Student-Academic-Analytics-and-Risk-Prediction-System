# Reproducibility guide

Everything in this repository can be rebuilt from a clean clone with the commands below.
The raw data and trained artefacts are **not** committed: the data are downloaded from UCI
and checksum-verified, and every model, result file and generated document is produced by
code from them.

## Fresh-clone procedure

From the repository root (Python 3.11+, Node.js 20.9+, network access for step 3 only):

| # | Command (run in) | What it does | Measured |
| --- | --- | --- | --- |
| 1 | `git clone …` | Clone the repository | — |
| 2 | `python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` (backend) | Backend environment | ~3 min with uv |
| 3 | `python -m analytics.data.download` (backend) | Download the UCI archive, extract the two CSVs, verify SHA-256 | 4 s |
| 4 | `python -m analytics.ml.train` (backend) | Nested CV for every model, cohort and scenario; persist the 12 selected pipelines; write `docs/ML_RESULTS.md` and the README results | 8 min 51 s |
| 5 | `python -m analytics.interpret.build` (backend) | Global importance and calibration; write `docs/INTERPRETABILITY.md` | 48 s |
| 6 | `uvicorn app.main:app --port 8000` (backend) | Start the API; `GET /api/v1/ready` → `"ready"` | seconds |
| 7 | `npm ci && npm run dev` (frontend) | Start the interface at <http://localhost:3000> | ~5 s install from cache |

Times were measured on an Apple-silicon laptop and are indicative only.

## Verified run (Phase 9)

On 2026-10-13 the steps above were run end to end in an empty directory, cloning the
public repository at commit `613c025`:

- **Before the data existed** (the condition CI runs in): Ruff passed; pytest reported 312
  passed and 65 skipped (the real-data and artefact tests), with no network access needed.
- **Download:** checksums verified for both cohort files.
- **Training and interpretability:** completed; the regenerated `docs/ML_RESULTS.md` and
  `docs/INTERPRETABILITY.md` matched the committed versions except for one line in the
  run-metadata table recording numpy 2.5.4 instead of 2.5.3 (the clean install resolved a
  newer patch release). No metric, selection or table value changed.
- **Tests with data and models:** 377 passed.
- **API:** `/api/v1/ready` reported `"ready"` with all five components available.
- **Frontend:** `npm ci`, lint, typecheck, 58 tests and the production build passed.

## Determinism

- The data are pinned by SHA-256; the download refuses files that do not match.
- One seed (42) drives the train/test split, every CV splitter, every estimator and the
  Shapley sampling; categories come from the data dictionary, not the data.
- Results depend on library versions. Each model's metadata records the Python,
  scikit-learn, NumPy, pandas, SciPy and joblib versions, and the loader refuses artefacts
  trained with a different scikit-learn version.

## Regenerating documents

| Document | Command (in `backend/`) | Staleness test |
| --- | --- | --- |
| `docs/DATA_DICTIONARY.md` | `python -m analytics.data.docgen` | `test_dictionary.py` |
| `docs/STATISTICAL_FINDINGS.md` | `python -m analytics.statistics.findings` | `test_real_dataset.py` |
| `docs/ML_RESULTS.md` and README results | `python -m analytics.ml.train --report-only` | `test_ml_real.py` |
| `docs/INTERPRETABILITY.md` | `python -m analytics.interpret.build` | `test_interpret_real.py` |
| README screenshots | `node scripts/screenshots.mjs` (API and production frontend running) | — |

The staleness tests run whenever the data and artefacts are present, so `./scripts/check.sh`
fails if any generated document no longer matches the code and artefacts.

## Continuous integration

`.github/workflows/ci.yml` runs Ruff, pytest, ESLint, TypeScript, Vitest and the
production build on every push and pull request. It deliberately does not download the
dataset or train models; tests that need them skip themselves, so CI checks code
correctness on synthetic data, while the verified run above checks the full pipeline.
