# Models

Trained artefacts are written here by the offline training pipeline
(`backend/analytics/ml/`, Phase 5). The API loads them read-only. Everything in
this directory except this README is **git-ignored**. The UCI data is not committed,
and artefacts are regenerated from it rather than versioned.

## Regenerating

From `backend/`, with the virtual environment active and the dataset downloaded:

```bash
python -m analytics.ml.train                 # full documented search, both cohorts (several minutes)
python -m analytics.ml.train --report-only   # rewrite docs/ML_RESULTS.md from saved results
python -m analytics.ml.train --search minimal --models-dir /tmp/models  # quick smoke run
```

The script verifies the dataset checksums first. With the same data and library
versions it reproduces the same results: seed 42 is used for the split, every CV
splitter and every estimator.

## Contents

```
models/
├── ml_results.json        every model's nested-CV folds, chosen parameters, test
│                          scores, selections, error analysis and run metadata
└── selected/
    ├── <cohort>__<task>__<scenario>.joblib   fitted preprocessing + estimator pipeline
    └── <cohort>__<task>__<scenario>.json     metadata for that pipeline
```

Only the **selected** model for each cohort (math, portuguese), task (regression,
classification) and scenario (early, mid_year, full_history) is persisted: 12 pipelines.
Other models are evaluated and reported, but their fitted pipelines are not stored.

Each metadata file records:
- the cohort, task, scenario and model;
- the input and encoded feature names and the target;
- the decision threshold and score type;
- the chosen hyperparameters and the search space;
- the seed, CV strategy, train/test sizes, and CV and test metrics;
- software versions, the dataset SHA-256, the artefact's own SHA-256 and the training
  timestamp.

`.joblib` files are pickles, so only load files produced by this pipeline. The loader
checks each file's SHA-256 against its metadata. It refuses artefacts trained with a
different scikit-learn version; retrain instead.
