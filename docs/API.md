# API reference

Base URL: `http://localhost:8000/api/v1`. Interactive schemas (OpenAPI):
<http://localhost:8000/docs>. Every response is JSON and typed with a Pydantic model; the
TypeScript types in `frontend/src/lib/{api,statistics,models,risk}.ts` mirror them.

## Conventions

| Topic | Rule |
| --- | --- |
| Cohorts | `cohort` ∈ `math`, `portuguese` |
| Scenarios | `scenario` ∈ `early` (no grades), `mid_year` (+ G1), `full_history` (+ G1, G2) |
| Tasks | `task` ∈ `regression` (predicts G3), `classification` (academic risk = G3 < 10) |
| Models | optional `model`; must be defined for the task, and only the selected (persisted) model per cohort/task/scenario can predict. Nothing is ever substituted. |
| Numbers | Full double precision; the frontend rounds for display. Undefined values are `null`, never `NaN`. Percentages are 0–100 (`*_percent`), proportions and CIs 0–1. |
| Pagination | Only `/dataset/records`: `page` ≥ 1, `page_size` 1–100 (default 25). |
| Request id | Every response carries `X-Request-ID` (sent value echoed, or generated). |
| Kinds | Results that could be confused carry a `kind`: `observed_historical`, `group_statistics`, `model_evaluation`, `individual_model_explanation`, `model_sensitivity`, `general_educational_suggestion`. |

### Errors

Every error has the body `{"code": "...", "detail": "..."}`. Details never include
server paths, settings or stack traces.

| Status | `code` | Meaning |
| --- | --- | --- |
| 404 | `not_found` | Unknown path |
| 404 | `model_not_available` | Model defined but not selected, so not persisted |
| 405 | `method_not_allowed` | Wrong HTTP method |
| 422 | `invalid_request` | Invalid parameter or body field (cohort, scenario, task, unknown model, page…) |
| 422 | `invalid_record` | Feature record with G3/`at_risk`, a grade the scenario does not allow, a missing or unknown attribute, or an undocumented value |
| 503 | `dataset_unavailable` | Dataset not downloaded (detail gives the command) |
| 503 | `dataset_invalid` | A cohort file fails validation, so analyses are refused (the quality report still works) |
| 503 | `models_unavailable` | No training run / interpretability results, or an artefact failed its integrity check |
| 500 | `internal_error` | Unexpected; logged server-side with the request id |

## System

| Endpoint | Returns |
| --- | --- |
| `GET /health` | Liveness: `status: "ok"`, version, environment. Always ok while the API runs. |
| `GET /ready` | `status: "ready" \| "degraded"` and one entry per component (`api`, `dataset`, `statistics`, `models`, `interpretability`) with `status` (`available`, `unavailable`, `degraded`), `detail` and the `action` command that fixes it. |
| `GET /project` | Project identity, dataset presence, module status. |
| `GET /dashboard/summary` | Readiness, per-cohort overview (rows, validation, G3 summary, **observed** risk with Wilson CI), selected models with CV and test primary metric (**model evaluation**), and notes separating the two. Unavailable parts are reported, not invented. |
| `GET /pipeline/summary?cohort=&scenario=` | The integrated pipeline for one cohort and scenario: step statuses (dataset, scenario, statistics, eda, models, explanations, risk) plus headlines from each. |

```bash
curl -s localhost:8000/api/v1/ready
curl -s "localhost:8000/api/v1/pipeline/summary?cohort=math&scenario=mid_year"
```

## Dataset explorer

| Endpoint | Returns |
| --- | --- |
| `GET /dataset/summary?cohort=` | Rows, columns, column types, missing/duplicate/invalid counts, validation status, source, target |
| `GET /dataset/schema?cohort=` | Data dictionary for the 33 columns plus observed values |
| `GET /dataset/quality?cohort=` | Validation checks, observations (e.g. G3 = 0), columns with issues |
| `GET /dataset/records?cohort=&page=&page_size=&search=` | Paginated raw records (`row` = 1-based file position, not an ID) |
| `GET /dataset/overlap` | Approximate cross-cohort matching and its caveats |
| `GET /preprocessing/summary?cohort=&scenario=` | Features, encoding, engineered features, exclusions, split |

## Statistics and EDA

| Endpoint | Returns |
| --- | --- |
| `GET /statistics/descriptive?cohort=` | Numeric summaries and categorical frequencies |
| `GET /statistics/distributions?cohort=` | G1–G3 distributions, shape, zero grades, observed risk |
| `GET /statistics/correlations?cohort=` | Key pairs with G3 (Holm), sensitivity without G3 = 0, Spearman matrix (BH) |
| `GET /statistics/hypothesis-tests?cohort=` | Research questions RQ1–RQ8 with tests, adjusted p, effect sizes |
| `GET /statistics/group-comparisons?cohort=&variable=` | One assumption-checked comparison (13 variables) |
| `GET /statistics/associations?cohort=` | Chi-square/Fisher vs academic risk, Cramér's V, BH |
| `GET /statistics/outliers?cohort=` | Tukey and z screening (flagged, never removed) |
| `GET /eda/charts?cohort=` | Chart-ready aggregates (largest response, ≈ 36 KB) |

## Model comparison

| Endpoint | Returns |
| --- | --- |
| `GET /models` | Model definitions and search spaces; run configuration and selected models once trained (`trained: false` otherwise, not an error) |
| `GET /models/regression?cohort=` | CV MAE/RMSE/R² (mean ± SD) and test metrics per scenario and model |
| `GET /models/classification?cohort=` | CV F1/ROC-AUC/recall/precision and test accuracy, balanced accuracy, precision, recall, specificity, F1, ROC-AUC |
| `GET /models/evaluations?cohort=&task=&scenario=` | Per-fold scores, chosen parameters, confusion matrix, diagnostics |
| `GET /models/scenario-comparison?cohort=&task=` | Selected model per scenario against the baseline |
| `GET /models/cohort-comparison` | Both cohorts side by side |
| `GET /models/selected?cohort=&task=&scenario=` | Persisted model metadata, selection rationale, test-set error analysis |

## Prediction

`POST /models/predict`

```json
{
  "cohort": "portuguese",
  "task": "classification",
  "scenario": "mid_year",
  "model": null,
  "features": {
    "school": "GP", "sex": "F", "age": 17, "address": "U", "famsize": "GT3",
    "Pstatus": "T", "Medu": 2, "Fedu": 3, "Mjob": "services", "Fjob": "other",
    "reason": "course", "guardian": "mother", "traveltime": 1, "studytime": 2,
    "failures": 0, "schoolsup": "no", "famsup": "yes", "paid": "no",
    "activities": "yes", "nursery": "yes", "higher": "yes", "internet": "yes",
    "romantic": "no", "famrel": 4, "freetime": 3, "goout": 3, "Dalc": 1,
    "Walc": 2, "health": 4, "absences": 0, "G1": 11
  }
}
```

The 30 non-grade attributes are always required, using the codes in
[DATA_DICTIONARY.md](DATA_DICTIONARY.md); `G1` only for `mid_year`/`full_history`,
`G2` only for `full_history`.

Response (`PredictionResult`): `cohort`, `task`, `scenario`, `model`, `model_label`;
regression → `predicted_grade` (limited to 0–20) and `raw_prediction`; classification
→ `at_risk`, `score`, `score_kind` (`probability` or `decision_function`), `threshold`,
and `probability` **only** when the model outputs probabilities (class-weighted, not
calibrated). Plus `model_test_metrics`, `trained_at` and `caveats`.

## Interpretability

| Endpoint | Returns |
| --- | --- |
| `GET /interpretability/importance?cohort=&task=&scenario=` | Global importance of the selected model: one entry per method (permutation on the test set, permutation on G3 > 0 for regression, mean \|Shapley\|, impurity or coefficients), each with unit, data and limitations; calibration for probability models |
| `POST /interpretability/explain` | Body as for prediction plus `top` (1–33). Returns the prediction and an `explanation`: Shapley contributions per attribute with standard errors, base value, method, background, limitations; `score_percentile` for classification |
| `POST /interpretability/sensitivity` | Body as for prediction plus `attribute` (studytime, absences, goout, freetime, traveltime, activities, paid, famsup, schoolsup, internet). Model output per value, with training support |
| `POST /interpretability/scenario-sensitivity` | `cohort`, `task`, `features` (G1/G2 optional): the record under each scenario its grades allow |

## Risk analysis

| Endpoint | Returns |
| --- | --- |
| `GET /risk/profiles?cohort=` | Observed at-risk proportions (Wilson CIs) for 8 school-related attributes and 3 two-way tables, with tests |
| `POST /risk/suggestions` | `cohort`, `scenario`, `features`: evidence-checked suggestions, those not shown and why, disclaimer |
| `POST /risk/insights` | Same body: `individual` (model explanation), `group` (observed group statistics for the record's values), `suggestions`, kept separate |

## Performance (measured)

Measured on a development laptop with `TestClient` against the official data and
persisted models, each request issued twice (cold = first request after start,
warm = cached). Values are indicative, not a benchmark.

| Request | Cold | Warm | Size |
| --- | --- | --- | --- |
| `GET /dataset/summary` | ≈ 40 ms (loads and validates the cohort) | ≈ 1.5 ms | 0.7 KB |
| `GET /statistics/hypothesis-tests` | ≈ 125 ms | ≈ 1.5 ms | 9.7 KB |
| `GET /eda/charts` | ≈ 23 ms | ≈ 1.5 ms | 36 KB |
| `GET /ready` | ≈ 105 ms (verifies checksums and loads the 12 models once) | ≈ 2 ms | 0.6 KB |
| `GET /dashboard/summary` | ≈ 6 ms | ≈ 2 ms | 5.3 KB |
| `POST /models/predict` | ≈ 15 ms | ≈ 13 ms | 0.9 KB |
| `POST /interpretability/explain` | ≈ 230 ms | ≈ 210 ms | 3.6 KB |
| `POST /risk/insights` | ≈ 420 ms | ≈ 410 ms | 7 KB |

Explanations are computed per request by design (≈ 35k model evaluations in one
batch); everything else is served from per-file-version caches.
