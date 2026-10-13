# Scripts

| Script | Purpose |
| --- | --- |
| `check.sh` | Every quality gate: Ruff, pytest, ESLint, TypeScript, Vitest (with axe-core) and a production build. Run before each commit; CI runs the same steps. |
| `screenshots.mjs` | Captures the README screenshots from the running application with headless Chrome (no extra dependencies). Needs the API on :8000 with data and models, and the production frontend on :3000. |

Data, model and document generation are Python modules in `backend/` (run from there with
the virtual environment active):

| Command | Produces |
| --- | --- |
| `python -m analytics.data.download` | `data/raw/` (checksum-verified UCI files) |
| `python -m analytics.data.docgen` | `docs/DATA_DICTIONARY.md` |
| `python -m analytics.statistics.findings` | `docs/STATISTICAL_FINDINGS.md` |
| `python -m analytics.ml.train` | `models/` (12 selected pipelines + results), `docs/ML_RESULTS.md`, README results |
| `python -m analytics.ml.train --report-only` | `docs/ML_RESULTS.md` and README results from saved results |
| `python -m analytics.interpret.build` | `models/interpretability.json`, `docs/INTERPRETABILITY.md` |

See [docs/REPRODUCIBILITY.md](../docs/REPRODUCIBILITY.md).
