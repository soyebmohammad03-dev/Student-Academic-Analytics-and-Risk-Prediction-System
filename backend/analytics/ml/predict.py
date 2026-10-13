"""Prediction service foundation: validated feature record in, structured prediction out.

A record holds the student's attributes exactly as the UCI files record them (e.g.
``absences`` as a count, ``Mjob`` as a code). Engineered features are derived here with
the same functions used in training. Validation is strict:

- an outcome (``G3``, ``at_risk``) in the record is a leakage error;
- ``G1``/``G2`` are accepted only when the scenario allows them, and are then required;
- every other attribute must be present, documented, and within its documented codes
  or range.

Only the model selected for each cohort, task and scenario is persisted, so ``model``
may be omitted (the selected one is used) or must name that model.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field
from sklearn.pipeline import Pipeline

from analytics.data import Cohort
from analytics.data.dictionary import COLUMNS, COLUMNS_BY_NAME
from analytics.ml.config import Task
from analytics.ml.metrics import positive_scores
from analytics.ml.persistence import load_metadata, load_pipeline
from analytics.ml.results import ArtifactMetadata, Metrics
from analytics.preprocessing import (
    RISK_THRESHOLD,
    SCENARIOS,
    TARGET_COLUMNS,
    LeakageError,
    Scenario,
    feature_columns,
)
from analytics.preprocessing.features import add_engineered_features
from analytics.preprocessing.scenarios import PRIOR_GRADES

GRADE_MIN, GRADE_MAX = 0, 20
RAW_FEATURES: tuple[str, ...] = tuple(c.name for c in COLUMNS if c.role == "feature")


class InvalidRecordError(ValueError):
    """The feature record is incomplete or contains undocumented values."""


class ModelNotAvailableError(LookupError):
    """The requested model was not selected, so it was not persisted."""


def required_attributes(scenario: Scenario) -> tuple[str, ...]:
    return RAW_FEATURES + SCENARIOS[Scenario(scenario)].prior_grades


def _check_value(name: str, value: Any) -> str | float:
    spec = COLUMNS_BY_NAME[name]
    if spec.measure == "categorical":
        if not isinstance(value, str) or value not in spec.allowed_codes:
            allowed = ", ".join(sorted(str(c) for c in spec.allowed_codes))
            raise InvalidRecordError(f"{name}: {value!r} is not one of {allowed}.")
        return value
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidRecordError(f"{name}: expected a whole number, got {value!r}.")
    if not math.isfinite(value) or float(value) != int(value):
        raise InvalidRecordError(f"{name}: expected a whole number, got {value!r}.")
    number = int(value)
    if spec.allowed and number not in spec.allowed_codes:
        allowed = ", ".join(str(c) for c in sorted(spec.allowed_codes))
        raise InvalidRecordError(f"{name}: {number} is not one of {allowed}.")
    if spec.minimum is not None and not spec.minimum <= number <= spec.maximum:
        raise InvalidRecordError(f"{name}: {number} is outside {spec.minimum}–{spec.maximum}.")
    return float(number)


def record_frame(record: Mapping[str, Any], scenario: Scenario) -> pd.DataFrame:
    """Validate one record and return the scenario's model input (one row)."""
    scenario = Scenario(scenario)
    keys = set(record)
    if leaked := keys & TARGET_COLUMNS:
        raise LeakageError(f"Outcome columns cannot be inputs: {sorted(leaked)}.")
    allowed_grades = set(SCENARIOS[scenario].prior_grades)
    if unavailable := (keys & set(PRIOR_GRADES)) - allowed_grades:
        raise LeakageError(f"{sorted(unavailable)} are not available in the '{scenario}' scenario.")
    required = required_attributes(scenario)
    if unknown := keys - set(required):
        raise InvalidRecordError(f"Unknown attributes: {sorted(unknown)}.")
    if missing := [name for name in required if name not in keys]:
        raise InvalidRecordError(f"Missing attributes: {missing}.")

    values = {name: _check_value(name, record[name]) for name in required}
    row = pd.DataFrame(
        {name: pd.Series([value], dtype=object if isinstance(value, str) else "float64")
         for name, value in values.items()}
    )  # fmt: skip
    return add_engineered_features(row)[list(feature_columns(scenario))]


class PredictionResult(BaseModel):
    cohort: Cohort
    task: Task
    scenario: Scenario
    model: str
    model_label: str
    predicted_grade: float | None = Field(
        default=None, description="Regression: predicted G3, limited to the 0–20 scale."
    )
    raw_prediction: float | None = Field(
        default=None, description="Regression: model output before limiting to 0–20."
    )
    at_risk: bool | None = Field(
        default=None, description=f"Classification: predicted G3 below {RISK_THRESHOLD}."
    )
    score: float | None = Field(default=None, description="Classification: continuous score.")
    score_kind: Literal["probability", "decision_function"] | None = None
    threshold: float | None = None
    model_test_metrics: Metrics
    trained_at: str
    caveats: list[str]


def _caveats(task: Task, scenario: Scenario) -> list[str]:
    notes = [
        "A statistical estimate from two Portuguese schools in 2005–2006; it does not "
        "describe an individual with certainty and is not a basis for decisions on its own.",
    ]
    if task is Task.CLASSIFICATION:
        notes.append(
            f"Academic risk means a final grade below {RISK_THRESHOLD} of 20. It is not a "
            "prediction of dropout."
        )
    if scenario is Scenario.EARLY:
        notes.append("Early scenario: no grade from the current year was used.")
    else:
        grades = " and ".join(SCENARIOS[scenario].prior_grades)
        notes.append(f"Uses {grades}, which are only known once those periods are graded.")
    return notes


class PredictionService:
    """Loads persisted pipelines lazily and caches them per artefact checksum."""

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self._cache: dict[str, tuple[ArtifactMetadata, Pipeline]] = {}
        self._lock = threading.Lock()

    def model(
        self, cohort: Cohort, task: Task, scenario: Scenario
    ) -> tuple[ArtifactMetadata, Pipeline]:
        meta = load_metadata(self.models_dir, str(cohort), Task(task), Scenario(scenario))
        with self._lock:
            cached = self._cache.get(meta.artifact)
            if cached is None or cached[0].sha256 != meta.sha256:
                cached = (meta, load_pipeline(self.models_dir, meta))
                self._cache[meta.artifact] = cached
            return cached

    def predict(
        self,
        cohort: Cohort,
        task: Task,
        scenario: Scenario,
        record: Mapping[str, Any],
        model: str | None = None,
    ) -> PredictionResult:
        task, scenario = Task(task), Scenario(scenario)
        X = record_frame(record, scenario)
        meta, pipeline = self.model(cohort, task, scenario)
        if model is not None and model != meta.model:
            raise ModelNotAvailableError(
                f"Only the selected model ({meta.model}) is persisted for {cohort} / {task} / "
                f"{scenario}; '{model}' is reported in the results but not stored."
            )
        X = X[meta.feature_columns]
        result = PredictionResult(
            cohort=Cohort(cohort),
            task=task,
            scenario=scenario,
            model=meta.model,
            model_label=meta.label,
            model_test_metrics=meta.test,
            trained_at=meta.created_at,
            caveats=_caveats(task, scenario),
        )
        if task is Task.REGRESSION:
            raw = float(pipeline.predict(X)[0])
            result.raw_prediction = raw
            result.predicted_grade = min(max(raw, GRADE_MIN), GRADE_MAX)
        else:
            result.at_risk = bool(int(pipeline.predict(X)[0]) == 1)
            result.score = float(positive_scores(pipeline, X)[0])
            result.score_kind = meta.score_kind
            result.threshold = meta.threshold
        return result
