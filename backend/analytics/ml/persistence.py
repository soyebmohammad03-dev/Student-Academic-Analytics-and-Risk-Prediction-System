"""Saving and loading training results and the selected models.

Layout (inside ``models/``, git-ignored and regenerated with
``python -m analytics.ml.train``)::

    models/
    ├── ml_results.json                         every model's CV and test results
    └── selected/
        ├── <cohort>__<task>__<scenario>.joblib fitted preprocessing + estimator pipeline
        └── <cohort>__<task>__<scenario>.json   ArtifactMetadata for that pipeline

Only the model selected for each cohort, task and scenario is persisted (12 pipelines).

Pipelines are serialised with ``joblib`` (pickle-based, as recommended by
scikit-learn). Pickle files can execute code when loaded, so the API only loads
artefacts from its own models directory, and ``load_pipeline`` refuses a file whose
SHA-256 does not match its metadata or that was produced with a different
scikit-learn version.
"""

from __future__ import annotations

import hashlib
import logging
import platform
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.pipeline import Pipeline

from analytics.data import COHORTS
from analytics.ml.config import SearchMode, Task, TrainingConfig
from analytics.ml.evaluation import TUNING_LABEL, Evaluation, describe_splitter
from analytics.ml.metrics import score_kind
from analytics.ml.registry import ESTIMATOR_STEP, get_spec, search_space
from analytics.ml.results import ArtifactMetadata, MlResults, ModelArtifactError, RunInfo
from analytics.ml.selection import METRIC_LABEL, PRIMARY_METRIC
from analytics.ml.training import TrainedCohort
from analytics.preprocessing import REGRESSION_TARGET, RISK_LABEL, TEST_SIZE, Scenario

log = logging.getLogger("analytics.ml")

SCHEMA_VERSION = 1
RESULTS_FILE = "ml_results.json"
SELECTED_DIR = "selected"


def software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "scikit-learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
    }


def artifact_stem(cohort: str, task: Task, scenario: Scenario) -> str:
    return f"{cohort}__{task}__{scenario}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_info(config: TrainingConfig, created_at: str | None = None) -> RunInfo:
    return RunInfo(
        schema_version=SCHEMA_VERSION,
        created_at=created_at or datetime.now(UTC).isoformat(timespec="seconds"),
        random_state=config.random_state,
        cv_folds=config.cv_folds,
        search=str(config.search),
        test_size=TEST_SIZE,
        cv_strategy={t: describe_splitter(t, config) for t in Task},
        tuning_metric=dict(TUNING_LABEL),
        selection_metric={t: METRIC_LABEL[m] for t, m in PRIMARY_METRIC.items()},
        decision_threshold=0.5,
        software=software_versions(),
        dataset_sha256={str(c): info.sha256 for c, info in COHORTS.items()},
    )


def _metadata(
    cohort: str, ev: Evaluation, run: RunInfo, artifact: Path, n_train: int, n_test: int
) -> ArtifactMetadata:
    task = ev.spec.task
    classification = task is Task.CLASSIFICATION
    kind = score_kind(ev.pipeline) if classification else None
    return ArtifactMetadata(
        cohort=cohort,
        task=task,
        scenario=ev.scenario,
        model=ev.spec.key,
        label=ev.spec.label,
        artifact=artifact.name,
        sha256=sha256(artifact),
        feature_columns=list(
            ev.pipeline.named_steps["prep"].named_steps["guard"].feature_names_in_
        ),
        encoded_features=[str(c) for c in ev.pipeline[:-1].get_feature_names_out()],
        target=RISK_LABEL if classification else REGRESSION_TARGET,
        positive_class="at_risk = 1 (G3 < 10)" if classification else None,
        threshold=(0.5 if kind == "probability" else 0.0) if classification else None,
        score_kind=kind,
        best_params=ev.best_params,
        search_space={
            k.removeprefix(f"{ESTIMATOR_STEP}__"): v
            for k, v in search_space(ev.spec, SearchMode(run.search)).items()
        },
        random_state=run.random_state,
        cv_folds=run.cv_folds,
        cv_strategy=run.cv_strategy[task],
        n_train=n_train,
        n_test=n_test,
        cv=ev.cv,
        test=ev.test,
        software=run.software,
        dataset_sha256=run.dataset_sha256[cohort],
        created_at=run.created_at,
    )


def save(trained: list[TrainedCohort], config: TrainingConfig, models_dir: Path) -> MlResults:
    """Write the selected pipelines, their metadata and the full results."""
    run = run_info(config)
    selected_dir = models_dir / SELECTED_DIR
    selected_dir.mkdir(parents=True, exist_ok=True)
    for stale in [*selected_dir.glob("*.joblib"), *selected_dir.glob("*.json")]:
        stale.unlink()

    for item in trained:
        cohort = item.results.cohort
        for (task, scenario), ev in item.selected.items():
            stem = artifact_stem(cohort, task, scenario)
            artifact = selected_dir / f"{stem}.joblib"
            joblib.dump(ev.pipeline, artifact, compress=3)
            meta = _metadata(cohort, ev, run, artifact, item.results.n_train, item.results.n_test)
            (selected_dir / f"{stem}.json").write_text(meta.model_dump_json(indent=2) + "\n")

    results = MlResults(run=run, cohorts=[t.results for t in trained])
    (models_dir / RESULTS_FILE).write_text(results.model_dump_json(indent=1) + "\n")
    return results


def load_results(models_dir: Path) -> MlResults:
    path = models_dir / RESULTS_FILE
    if not path.is_file():
        raise ModelArtifactError(
            "No training results found. Run `python -m analytics.ml.train` from backend/."
        )
    try:
        return MlResults.model_validate_json(path.read_text())
    except ValueError as exc:
        raise ModelArtifactError(
            f"{RESULTS_FILE} is unreadable or from an incompatible version; retrain."
        ) from exc


def load_metadata(
    models_dir: Path, cohort: str, task: Task, scenario: Scenario
) -> ArtifactMetadata:
    path = models_dir / SELECTED_DIR / f"{artifact_stem(cohort, task, scenario)}.json"
    if not path.is_file():
        raise ModelArtifactError(f"No persisted model for {cohort} / {task} / {scenario}.")
    return ArtifactMetadata.model_validate_json(path.read_text())


def load_pipeline(models_dir: Path, meta: ArtifactMetadata) -> Pipeline:
    path = models_dir / SELECTED_DIR / meta.artifact
    if not path.is_file():
        raise ModelArtifactError(f"Model file {meta.artifact} is missing.")
    if sha256(path) != meta.sha256:
        raise ModelArtifactError(f"{meta.artifact} does not match its recorded SHA-256.")
    trained_with = meta.software.get("scikit-learn")
    if trained_with != sklearn.__version__:
        raise ModelArtifactError(
            f"{meta.artifact} was trained with scikit-learn {trained_with}; this environment "
            f"has {sklearn.__version__}. Retrain with `python -m analytics.ml.train`."
        )
    try:
        pipeline = joblib.load(path)
    except Exception as exc:  # corrupted or truncated pickle
        raise ModelArtifactError(f"{meta.artifact} could not be loaded; retrain.") from exc
    _check_contents(pipeline, meta)
    log.info("model loaded", extra={"artifact": meta.artifact, "model": meta.model})
    return pipeline


def _check_contents(pipeline, meta: ArtifactMetadata) -> None:
    """The loaded object must be the pipeline its metadata describes."""
    expected = type(get_spec(meta.task, meta.model).factory(0))
    try:
        estimator = pipeline.named_steps["model"]
        inputs = list(pipeline.named_steps["prep"].named_steps["guard"].feature_names_in_)
    except (AttributeError, KeyError) as exc:
        raise ModelArtifactError(f"{meta.artifact} is not a preprocessing pipeline.") from exc
    if type(estimator) is not expected:
        raise ModelArtifactError(
            f"{meta.artifact} contains {type(estimator).__name__}, but its metadata says "
            f"{meta.model}."
        )
    if inputs != meta.feature_columns:
        raise ModelArtifactError(f"{meta.artifact} expects different inputs than its metadata.")
