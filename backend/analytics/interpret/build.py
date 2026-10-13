"""Compute global interpretability results for the persisted models.

Usage (from backend/, after ``python -m analytics.ml.train``)::

    python -m analytics.interpret.build

Writes ``models/interpretability.json`` and ``docs/INTERPRETABILITY.md``. Nothing is
retrained: every result is computed from the 12 persisted pipelines, the training
split (background) and the held-out test split (scored only).
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from analytics.data import COHORTS, Cohort, load_cohort
from analytics.data.download import DEFAULT_RAW_DIR, verify
from analytics.interpret.attributes import attributes, model_input
from analytics.interpret.importance import (
    GLOBAL_SHAPLEY_SAMPLES,
    PERMUTATION_REPEATS,
    calibration,
    coefficient_importance,
    impurity_importance,
    mean_abs_shapley,
    model_output,
    permutation_importance,
)
from analytics.interpret.results import InterpretabilityRun, ModelInterpretation
from analytics.ml.config import DEFAULT_MODELS_DIR, Task
from analytics.ml.persistence import load_results, software_versions
from analytics.ml.predict import PredictionService
from analytics.ml.results import ModelArtifactError
from analytics.preprocessing import AnalyticalDataset, Scenario, prepare_cohort
from analytics.risk.results import RiskProfiles

SCHEMA_VERSION = 1
RESULTS_FILE = "interpretability.json"


def interpret_model(
    service: PredictionService,
    dataset: AnalyticalDataset,
    task: Task,
    scenario: Scenario,
    *,
    repeats: int = PERMUTATION_REPEATS,
    shapley_samples: int = GLOBAL_SHAPLEY_SAMPLES,
    shapley_rows: int | None = None,
) -> ModelInterpretation:
    meta, pipeline = service.model(dataset.cohort, task, scenario)
    if meta.dataset_sha256 != COHORTS[dataset.cohort].sha256:
        raise ModelArtifactError("The persisted model was trained on different data.")
    split = dataset.split(scenario, random_state=meta.random_state)
    names = list(attributes(scenario))
    train_raw = dataset.analytical.loc[split.train_index, names]
    test_raw = dataset.analytical.loc[split.test_index, names]
    y_test = split.y_test_regression if task is Task.REGRESSION else split.y_test_risk

    methods = [
        permutation_importance(meta, pipeline, test_raw, y_test, repeats=repeats),
        mean_abs_shapley(
            meta,
            pipeline,
            test_raw if shapley_rows is None else test_raw.iloc[:shapley_rows],
            train_raw,
            n_samples=shapley_samples,
        ),
    ]
    if task is Task.REGRESSION and (y_test == 0).any():
        nonzero = y_test > 0
        methods.append(
            permutation_importance(
                meta,
                pipeline,
                test_raw[nonzero],
                y_test[nonzero],
                repeats=repeats,
                subset="G3 > 0 only",
            )
        )
    methods += [
        m
        for m in (impurity_importance(meta, pipeline), coefficient_importance(meta, pipeline))
        if m
    ]
    cal = None
    if task is Task.CLASSIFICATION:
        scores = model_output(pipeline, task)(model_input(test_raw, scenario))
        cal = calibration(meta, scores, y_test.to_numpy(dtype=float))
    return ModelInterpretation(
        cohort=meta.cohort,
        task=task,
        scenario=scenario,
        model=meta.model,
        model_label=meta.label,
        methods=methods,
        calibration=cal,
    )


def build(
    raw_dir: Path,
    models_dir: Path,
    *,
    repeats: int = PERMUTATION_REPEATS,
    shapley_samples: int = GLOBAL_SHAPLEY_SAMPLES,
) -> InterpretabilityRun:
    results = load_results(models_dir)
    service = PredictionService(models_dir)
    items = []
    for cohort in Cohort:
        dataset = prepare_cohort(load_cohort(raw_dir, cohort))
        for task in Task:
            for scenario in (Scenario.EARLY, Scenario.MID_YEAR, Scenario.FULL_HISTORY):
                items.append(
                    interpret_model(
                        service,
                        dataset,
                        task,
                        scenario,
                        repeats=repeats,
                        shapley_samples=shapley_samples,
                    )
                )
    return InterpretabilityRun(
        schema_version=SCHEMA_VERSION,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        models_created_at=results.run.created_at,
        random_state=results.run.random_state,
        permutation_repeats=repeats,
        shapley_samples=shapley_samples,
        software=software_versions(),
        items=items,
    )


def load(models_dir: Path) -> InterpretabilityRun:
    path = models_dir / RESULTS_FILE
    if not path.is_file():
        raise ModelArtifactError(
            "No interpretability results. Run `python -m analytics.interpret.build` from backend/."
        )
    return InterpretabilityRun.model_validate_json(path.read_text())


def cohort_profiles(raw_dir: Path) -> dict[str, RiskProfiles]:
    from analytics.risk.profiles import risk_profiles

    return {
        str(c): risk_profiles(prepare_cohort(load_cohort(raw_dir, c)).analytical, str(c))
        for c in Cohort
    }


def save(run: InterpretabilityRun, models_dir: Path) -> None:
    (models_dir / RESULTS_FILE).write_text(run.model_dump_json(indent=1) + "\n")


def main() -> int:
    from analytics.interpret.report import OUTPUT, render

    if problems := verify(DEFAULT_RAW_DIR):
        print("Dataset verification failed:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    start = time.perf_counter()
    run = build(DEFAULT_RAW_DIR, DEFAULT_MODELS_DIR)
    save(run, DEFAULT_MODELS_DIR)
    OUTPUT.write_text(render(run, cohort_profiles(DEFAULT_RAW_DIR)), encoding="utf-8")
    print(
        f"Wrote {DEFAULT_MODELS_DIR / RESULTS_FILE} and {OUTPUT} "
        f"in {time.perf_counter() - start:.0f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
