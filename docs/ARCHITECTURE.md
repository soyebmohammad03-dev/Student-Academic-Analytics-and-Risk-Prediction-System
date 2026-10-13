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
| `analytics/pipeline.py` | Unified pipeline: per-file-version caches, readiness, dashboard and pipeline summaries (Phase 7) |
| `app/core/logging.py`   | Structured JSON logging (Phase 7) |
| `analytics/interpret/`  | Attribute mapping, permutation-sampling Shapley values, global importance, calibration, individual explanations, sensitivity experiments, interpretability report (Phase 6) |
| `analytics/risk/`       | Group-level academic-risk profiles and evidence-checked suggestions (Phase 6) |
| `analytics/ml/`         | Model registry, nested CV and tuning, metrics, selection, error analysis, comparisons, persistence, prediction service, results report (Phase 5) |

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
and fits it on `split.X_train` (see below). Training stays offline; the API only reads
results and persisted pipelines.

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

## Machine-learning layer (Phase 5)

```
AnalyticalDataset ── split(scenario) ──▶ X_train / X_test (Phase 3 split, seed 42)
        │
registry.py   ModelSpec: estimator factory, grid, complexity, class_weight
        └─ build_pipeline(spec, scenario) = Pipeline[prep (ScenarioGuard + encoders), model]
evaluation.py
        ├─ nested_cv: outer K/StratifiedKFold(5) × GridSearchCV(inner 5) on X_train only
        ├─ final fit: GridSearchCV on all of X_train → best pipeline
        └─ one-off test scoring (metrics.py: ROC-AUC from scores, None when undefined)
training.py   train_cohort: 3 scenarios × 2 tasks × all models
        ├─ selection.py   CV-only rule: primary metric, one-SE, simplest
        ├─ errors.py      residual / confusion analysis of selected models
        └─ diagnostics    near-perfect, single-class, CV–test gap, below baseline
comparison.py regression / classification tables, scenario and cohort comparisons
persistence.py models/ml_results.json + models/selected/<cohort>__<task>__<scenario>.{joblib,json}
predict.py    record validation (dictionary + leakage) → persisted pipeline → PredictionResult
report.py     docs/ML_RESULTS.md (written by train.py; a test checks it is current)
```

- **Offline training.** `python -m analytics.ml.train` checks the dataset checksums,
  trains, selects, saves and writes the report (a few minutes). The API never trains.
- **Artefacts.** Only the 12 selected pipelines are persisted (one per cohort, task
  and scenario), each with JSON metadata. `models/` is git-ignored, like `data/raw/`.
- **Loading safety.** `joblib` files are pickles. They are loaded only from the
  configured models directory. Loading checks each file's SHA-256 against its
  metadata and refuses one built with another scikit-learn version.
- **Serving.** `app/services/models.py` caches `ml_results.json` until the file
  changes. `PredictionService` caches each loaded pipeline by artefact checksum.
- **Result types.** These are Pydantic models in `analytics/ml/results.py` and
  `comparison.py`, reused as API response models, as in the statistics layer.

**Frontend.** The model-comparison page is marked *in progress*. Phase 5 delivers results
through the API and `docs/ML_RESULTS.md`; the page is built in Phase 8.

## Interpretability and risk layer (Phase 6)

```
persisted pipelines (models/selected) ─┐        cohort data (DatasetStore → AnalyticalDataset)
                                       ▼                         │ training split = background
attributes.py   encoded/engineered columns ↔ original attributes │
shapley.py      permutation-sampling interventional Shapley (attribute players, batched)
importance.py   permutation (test) · mean |Shapley| · impurity · coefficients · calibration
explain.py      Interpreter: explain(record) · sensitivity(attribute) · scenario_sensitivity
build.py        CLI → models/interpretability.json + docs/INTERPRETABILITY.md (no retraining)
risk/profiles.py     observed risk by pre-defined school-related groups (reuses Phase 4 tests)
risk/suggestions.py  rules → Fisher evidence check → suggestions / not_shown + disclaimer
```

- **Offline vs on demand.** Global importance (about 45 s for 12 models) is computed
  offline. The API serves it from `interpretability.json`, which is cached until the
  file changes. Explanations, sensitivity, profiles and suggestions are computed per
  request. Each explanation is one batched Shapley estimate of about 35k rows, under a
  second for the forests.
- **Service.** `app/services/interpretability.py` (`RiskService`) combines the
  `DatasetStore`, used for background data and profiles, with the `ModelStore`, used
  for the persisted pipelines. It caches the analytical dataset and profiles per
  cohort version.
- **Separation of statements.** Response types carry a `kind`:
  `individual_model_explanation`, `model_sensitivity`, `group_statistics` or
  `general_educational_suggestion`. `/risk/insights` returns the three kinds in
  separate fields.
- **No new dependency.** SHAP is not used (see METHODOLOGY §7.2).

**Frontend.** The Risk Analysis page (`/risk-analysis`) consumes `/risk/profiles`
and `/interpretability/importance`:
- profiles show bars with 95% intervals and the cohort rate;
- importance shows one card per method, each on its own scale, with its limitations.

The Prediction page is marked *in progress*. Its services exist in the API, and the
input form is Phase 8 work.

## Integrated backend (Phase 7)

```
                       ┌──────────────── AnalyticsPipeline (analytics/pipeline.py) ────────────────┐
data/raw/*.csv ──stamp─▶ cohort(c) → CohortVersion: loaded · validation · dataset (prepared)       │
                       │                 ├─ statistics → CohortAnalysis (descriptive … eda)        │
                       │                 ├─ preprocessing_report(scenario)                         │
                       │                 ├─ profiles (risk)                                        │
                       │                 └─ explain_data(seed) (Shapley background)                │
models/ml_results.json ─stamp─▶ ml_results()                                                         │
models/selected/*      ──────▶ predictions: PredictionService (sha-checked, cached per checksum)    │
models/interpretability.json ─stamp─▶ interpretability() · importance(c, task, scenario)            │
                       │ interpreter: Interpreter(predictions, cohort data)                        │
                       │ readiness() · overview(c) · selected_models() · summary(c, scenario)      │
                       └────────────────────────────────────────────────────────────────────────────┘
          ▲ one instance per (data dir, models dir): app/api/deps.py `get_pipeline`
          │
  DatasetStore · ModelStore · RiskService · get_analysis  (thin API views in app/services)
```

- **One owner for every cache.** Before Phase 7, the statistics, preprocessing, model
  and risk services each kept their own cache, and each cohort was prepared up to
  three times. Now one `AnalyticsPipeline` per settings owns them all:
  - **Cohort files:** a `FileCache` keyed on modification time and size holds one
    `CohortVersion` per file version. Everything derived from that version (prepared
    dataset, statistics, preprocessing reports, risk profiles, explanation
    background) is computed lazily, once.
  - **Model artefacts:** training results and interpretability results are cached the
    same way. The prediction service caches each pipeline per artefact checksum.

  A changed file produces a new entry on the next request, so stale results are never
  served. Tests cover this.
- **No hidden work.** API startup and requests never download data or train models.
  Those are explicit commands, and tests fail if a request calls them.
- **Readiness.** `GET /ready` reports each component separately:
  - **API:** always available while it responds.
  - **Dataset:** both files present and matching their pinned checksums.
  - **Statistics:** available when the dataset is present and validates.
  - **Models:** every selected artefact present, checksum-verified, loadable, built
    with this scikit-learn version, and matching its metadata (estimator class and
    inputs).
  - **Interpretability:** present and built from the current training run.

  The overall status is `ready` or `degraded`, never a false "ready". Each missing
  component names the command that fixes it.
- **Model integrity.** `load_pipeline` refuses an artefact whose checksum, scikit-learn
  version, estimator class or input columns disagree with its metadata. A corrupted
  pickle becomes `ModelArtifactError` (API: `503 models_unavailable`), not a crash.
- **Errors and logging.**
  - Every error body is `{code, detail}`, including 404, 405 and unexpected 500s.
  - Messages never contain server paths, settings or tracebacks.
  - Logs are JSON lines on stderr: one `request` line per call (method, path, status,
    `duration_ms`, `request_id`), a warning for each rejected request, and the full
    traceback for unexpected errors.
  - The level is set by `SAARPS_LOG_LEVEL`, and `X-Request-ID` links a client report
    to the log line.
- **Dashboard and pipeline summaries.**
  - `GET /dashboard/summary` reports observed cohort facts (`kind: observed_historical`)
    separately from model evaluation scores (`kind: model_evaluation`). It degrades
    gracefully when artefacts are missing.
  - `GET /pipeline/summary` runs every step for one cohort and scenario and reports
    each step's availability. The same summary is available offline with
    `python -m analytics.pipeline --cohort math --scenario early`.

Measured request times and response sizes are in [API.md](API.md#performance-measured).
They do not justify extra infrastructure such as Redis: warm requests take about 1–2 ms,
explanations about 0.2 s by design, and the largest response is about 36 KB.

### Breaking API changes in Phase 7

- 404 and 405 responses now use `{code, detail}` (`not_found`, `method_not_allowed`)
  instead of FastAPI's `{detail}`.
- `dataset_unavailable` and `models_unavailable` details no longer include server
  paths.
- An unknown `model` name now returns `422 invalid_request`. A defined but unpersisted
  model still returns `404 model_not_available`.
- A cohort file that fails validation returns `503 dataset_invalid` from analysis
  endpoints, instead of an unhandled 500.
- Permutation and Shapley importance items are ranked by value (largest first);
  previously they were ranked by absolute value. Only coefficients rank by magnitude.
  `interpretability.json` and `INTERPRETABILITY.md` were rebuilt without retraining.

## API (current)

All paths are under `/api/v1`. A request/response reference for the frontend is in [API.md](API.md). `cohort` is required where listed and must be `math`
or `portuguese`.

| Method | Path               | Parameters | Description |
| ------ | ------------------ | ---------- | ----------- |
| GET    | `/health`          | — | Liveness, version and environment |
| GET    | `/ready`           | — | Component readiness (api, dataset, statistics, models, interpretability) |
| GET    | `/dashboard/summary` | — | Observed cohort overview, selected-model evaluation, readiness |
| GET    | `/pipeline/summary` | `cohort`, `scenario` | Every pipeline step for one cohort and scenario, with availability |
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
| GET    | `/models` | — | Model definitions and search spaces; run configuration and the selected model per cohort/task/scenario once trained |
| GET    | `/models/regression` | `cohort` | G3 regression table: CV MAE/RMSE/R² (mean ± SD) and test MAE/RMSE/R² for every scenario and model, with selections |
| GET    | `/models/classification` | `cohort` | Academic-risk table: CV F1/ROC-AUC/recall/precision and test accuracy, precision, recall, specificity, F1, ROC-AUC, balanced accuracy |
| GET    | `/models/evaluations` | `cohort`, `task`, `scenario` | Full records: per-fold scores, parameters chosen per fold, test confusion matrix, diagnostics |
| GET    | `/models/scenario-comparison` | `cohort`, `task` | Selected model per scenario (early → mid-year → full history) against the baseline |
| GET    | `/models/cohort-comparison` | — | Sample sizes, G3 and risk distributions, selected models for both cohorts |
| GET    | `/models/selected` | `cohort`, `task`, `scenario` | Persisted model metadata, selection rationale, test-set error analysis |
| POST   | `/models/predict` | body: `cohort`, `task`, `scenario`, optional `model`, `features` | Prediction from a validated feature record, with caveats |
| GET    | `/interpretability/importance` | `cohort`, `task`, `scenario` | Global importance of the selected model, one entry per method (unit, data, limitations), plus probability calibration |
| POST   | `/interpretability/explain` | body: `cohort`, `task`, `scenario`, optional `model`, `features`, `top` (1–33) | Prediction plus Shapley contributions (with SE), base value, score percentile, limitations |
| POST   | `/interpretability/sensitivity` | body: as above plus `attribute` (10 school-related attributes) | Model output as one attribute varies, with training support per value |
| POST   | `/interpretability/scenario-sensitivity` | body: `cohort`, `task`, `features` (G1/G2 optional) | The record predicted under each scenario its grades allow |
| GET    | `/risk/profiles` | `cohort` | Observed at-risk proportions with Wilson CIs for 8 attributes and 3 two-way tables |
| POST   | `/risk/suggestions` | body: `cohort`, `scenario`, `features` | Evidence-checked suggestions, suggestions not shown and why, disclaimer |
| POST   | `/risk/insights` | body: `cohort`, `scenario`, `features` | A. individual explanation · B. group findings · C. suggestions, kept separate |

Errors use one shape, `{"code": "...", "detail": "..."}`:

| Status | `code` | When |
| ------ | ------ | ---- |
| 422 | `invalid_request` | Unknown cohort, scenario or comparison variable, missing cohort, page or page size out of range, search too long |
| 404 | `not_found` / 405 `method_not_allowed` | Unknown path or method |
| 503 | `dataset_unavailable` | Dataset files not downloaded; `detail` gives the command |
| 503 | `dataset_invalid` | A cohort file fails validation; analyses are refused |
| 500 | `internal_error` | Unexpected error; logged with the request id, no internals in the body |
| 422 | `invalid_record` | Prediction, explanation, sensitivity or risk record with an outcome column, a grade the scenario does not allow, a missing or unknown attribute, or an undocumented value |
| 404 | `model_not_available` | Prediction requested from a model that was evaluated but not selected (only selected models are persisted) |
| 503 | `models_unavailable` | No training run or interpretability results in `models/`, or an artefact failed its checksum/version check; `detail` gives the command |
