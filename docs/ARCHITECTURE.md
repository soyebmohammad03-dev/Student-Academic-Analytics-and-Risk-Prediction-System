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
| `analytics/preprocessing/` | Targets, feature scenarios, leakage guards, sklearn preprocessor, split, report (Phase 3) |
| `analytics/statistics/` | Descriptive stats, distributions, correlations, group comparisons, chi-square, outliers, research questions, EDA chart data, findings generator (Phase 4) |
| `analytics/` (other)    | Modelling (Phase 5) |

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

## Preprocessing layer (Phase 3)

```
LoadedCohort + ValidationReport
        │ prepare_cohort()            (refuses a cohort that failed validation)
        ▼
AnalyticalDataset ── raw (untouched) · validated · analytical (+ engineered, G3, at_risk)
        │
        ├─ features(scenario) ─▶ FeatureMatrix(scenario, X)     outcomes never included
        ├─ regression_target() / risk_target()
        └─ split(scenario) ────▶ Split(X_train, X_test, y_*_regression, y_*_risk)
                                   stratified on at_risk, random_state=42, shared by tasks

build_preprocessor(scenario, scale_numeric) ─▶ unfitted Pipeline
        ScenarioGuard  →  ColumnTransformer(binary OHE | nominal OHE | ordinal | numeric | indicator)

build_report(dataset, scenario) ─▶ PreprocessingReport (fits the preprocessor on train only)
```

Phase 5 composes `Pipeline([("prep", build_preprocessor(s)), ("model", estimator)])`
and fits it on `split.X_train`. Training stays offline; the API only reads metadata.

`app/services/preprocessing.py` builds each report once per cohort version, reusing
the `DatasetStore` cache, and exposes it through a single metadata endpoint. The
frontend does not depend on it in this phase.

## Statistics layer (Phase 4)

```
AnalyticalDataset.analytical  (validated values + at_risk; G3 = 0 kept)
        │
        ├─ descriptive.describe ─────────▶ DescriptiveStatistics
        ├─ distributions.distributions ──▶ Distributions (G1–G3, risk, zero-grade notes)
        ├─ correlation.correlations ─────▶ Correlations (key pairs + sensitivity + matrix)
        ├─ comparisons.compare_groups ───▶ GroupComparison (assumptions → test → post-hoc)
        ├─ association.associations ─────▶ Associations (chi-square / Fisher, Cramér's V)
        ├─ outliers.outliers ────────────▶ Outliers (Tukey, z)
        ├─ research.research_questions ──▶ ResearchQuestions (Holm family + exploratory)
        └─ eda.eda ──────────────────────▶ Eda (chart-ready aggregates)

core.py: CIs, effect sizes, Holm/BH, Welch ANOVA, Games–Howell, Dunn
findings.py → docs/STATISTICAL_FINDINGS.md (generated; a test checks it is current)
```

- **Result types.** Results are Pydantic models defined in `analytics/statistics/models.py`
  and reused directly as API response models. This avoids a duplicate schema layer.
  Pydantic is a library dependency, so `analytics` still never imports `app`.
- **JSON safety.** Undefined floats become `null`, never NaN.
- **Caching.** `app/services/statistics.py` builds a `CohortAnalysis` per cohort version
  (keyed on the `DatasetStore` entry) and computes each analysis lazily, once.
- **Why not statsmodels.** Welch's ANOVA, Games–Howell and Dunn's test are not in SciPy.
  They are implemented in `core.py` and verified by exact identities in the tests:
  - Welch's ANOVA with two groups equals Welch's t²;
  - Games–Howell with two groups equals Welch's t-test;
  - Dunn's z² with two groups equals Kruskal–Wallis H.

  So statsmodels is not needed.

**Frontend.** `/statistics` and `/eda` consume these endpoints through `useApi`.
Reusable SVG charts live in `src/components/charts/` (Histogram, BarList, BoxPlot,
Scatter, Heatmap). Each has a hover tooltip and a "Show data" table. The chart colour
tokens in `globals.css` were validated for colour-vision deficiency in light and dark
mode.

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
| GET    | `/statistics/descriptive` | `cohort` | Numeric summaries (count, mean + CI, median, modes, range, variance, SD, quartiles, IQR, skewness, kurtosis); categorical frequencies |
| GET    | `/statistics/distributions` | `cohort` | G1/G2/G3 counts 0–20, shape, normality, zero grades, risk proportion with Wilson CI |
| GET    | `/statistics/correlations` | `cohort` | Key pairs with G3 (method, r, CI, p, Holm p, n, interpretation), sensitivity without G3 = 0, Spearman matrix (BH) |
| GET    | `/statistics/hypothesis-tests` | `cohort` | Research questions: hypotheses, test, statistic, p, Holm p, effect size + CI, finding, sensitivity |
| GET    | `/statistics/group-comparisons` | `cohort`, `variable` (13 options) | Group summaries and box statistics, normality and Levene checks, selected test, effect sizes, post-hoc |
| GET    | `/statistics/associations` | `cohort` | Chi-square/Fisher vs `at_risk`: contingency rows, V, BH p |
| GET    | `/statistics/outliers` | `cohort` | Tukey fences and z-scores per variable; flagged values |
| GET    | `/eda/charts` | `cohort` | Histograms, bars, box plots, aggregated scatters, heatmap, risk profile, cross-tab |
| GET    | `/preprocessing/summary` | `cohort`, `scenario` (`full_history` \| `mid_year` \| `early`, default `early`) | Shapes, feature groups, encoded features (fitted on train), engineered features, excluded columns and why, missing-value handling, target and risk distributions, outliers, split |

Errors use one shape, `{"code": "...", "detail": "..."}`:

| Status | `code` | When |
| ------ | ------ | ---- |
| 422 | `invalid_request` | Unknown cohort, scenario or comparison variable, missing cohort, page or page size out of range, search too long |
| 503 | `dataset_unavailable` | Dataset files not downloaded; `detail` gives the command |
