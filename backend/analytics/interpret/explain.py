"""Individual explanations and model-sensitivity experiments for persisted models.

- ``explain``: the prediction plus Shapley contributions of each attribute to the
  model output, relative to the average output over training students.
- ``sensitivity``: the model output when one modifiable attribute is varied over its
  documented values, every other input held fixed.
- ``scenario_sensitivity``: the same record predicted under each scenario its grades
  allow.

All three describe **model behaviour**. They do not explain why a real student has an
outcome, and they do not show what would happen if a student changed something.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from analytics.data import Cohort
from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.interpret.attributes import (
    attribute_label,
    attributes,
    model_input,
    value_label,
)
from analytics.interpret.importance import model_output, output_label
from analytics.interpret.results import (
    Contribution,
    ExplainedPrediction,
    Explanation,
    ScenarioPrediction,
    ScenarioSensitivity,
    SensitivityCurve,
    SensitivityPoint,
)
from analytics.interpret.shapley import DEFAULT_SEED, shapley_values
from analytics.ml.config import Task
from analytics.ml.predict import (
    GRADE_MAX,
    GRADE_MIN,
    InvalidRecordError,
    ModelNotAvailableError,
    PredictionService,
    validated_record,
)
from analytics.preprocessing import (
    SCENARIOS,
    TARGET_COLUMNS,
    AnalyticalDataset,
    LeakageError,
    Scenario,
)
from analytics.statistics.config import MIN_GROUP_SIZE

#: Samples for a single on-demand explanation (≈ 35k model evaluations, one batch).
EXPLANATION_SAMPLES = 1024
TOP_CONTRIBUTIONS = 10
#: Attributes offered for sensitivity experiments: school-related behaviours and
#: support. Demographic and family-background attributes are deliberately excluded.
SENSITIVITY_ATTRIBUTES: tuple[str, ...] = (
    "studytime",
    "absences",
    "goout",
    "freetime",
    "traveltime",
    "activities",
    "paid",
    "famsup",
    "schoolsup",
    "internet",
)
ABSENCE_GRID: tuple[int, ...] = (0, 2, 4, 6, 8, 10, 15, 20, 30)
ABSENCE_BANDS: tuple[tuple[int, int], ...] = ((0, 0), (1, 5), (6, 10), (11, 20), (21, 93))

EXPLANATION_LIMITATIONS = [
    "Explains how the selected model arrived at this output. It does not explain why a "
    "real student has a particular outcome, and it is not a statement about cause.",
    "Contributions are measured against the average output over training students; a "
    "different reference group would give different values.",
    "Interventional Shapley values combine this record's values with other students' "
    "values attribute by attribute, which can create atypical combinations of inputs.",
    "Monte Carlo estimate: contributions within about two standard errors of 0 are "
    "marked negligible.",
]

SENSITIVITY_NOTE = (
    "Model sensitivity experiment: one attribute is changed in the model input while every "
    "other input stays as entered. It shows how the model responds, not what would happen "
    "if a student changed this in real life. Values held by few training students "
    "(marked sparse) lie where the model has little data."
)


@dataclass(frozen=True)
class CohortData:
    """Training rows used as background and reference for one cohort."""

    train: pd.DataFrame  # raw attributes of every training student
    #: Training students with G3 = 0, and how many of them have 0 absences.
    zero_grades: int = 0
    zero_grades_without_absences: int = 0

    @classmethod
    def from_dataset(cls, dataset: AnalyticalDataset, random_state: int) -> CohortData:
        split = dataset.split(Scenario.FULL_HISTORY, random_state=random_state)
        columns = list(attributes(Scenario.FULL_HISTORY))
        train = dataset.analytical.loc[split.train_index]
        zero = train["G3"] == 0
        return cls(
            train=train[columns],
            zero_grades=int(zero.sum()),
            zero_grades_without_absences=int((train.loc[zero, "absences"] == 0).sum()),
        )


class Interpreter:
    """Explanations for the persisted models, with training data as the reference."""

    def __init__(self, service: PredictionService, data: Callable[[Cohort, int], CohortData]):
        self.service = service
        self._data = data
        self._scores: dict[tuple[str, str], np.ndarray] = {}
        self._lock = threading.Lock()

    def _context(self, cohort, task, scenario, model):
        meta, pipeline = self.service.model(Cohort(cohort), Task(task), Scenario(scenario))
        if model is not None and model != meta.model:
            raise ModelNotAvailableError(
                f"Only the selected model ({meta.model}) is persisted for {cohort} / {task} / "
                f"{scenario}; '{model}' is not stored."
            )
        return meta, pipeline, self._data(Cohort(cohort), meta.random_state)

    def _training_scores(self, meta, pipeline, data: CohortData) -> np.ndarray:
        key = (meta.artifact, meta.sha256)
        with self._lock:
            if key not in self._scores:
                X = model_input(data.train, meta.scenario)
                self._scores[key] = model_output(pipeline, meta.task)(X)
            return self._scores[key]

    def explain(
        self,
        cohort: Cohort,
        task: Task,
        scenario: Scenario,
        record: Mapping[str, Any],
        model: str | None = None,
        *,
        top: int = TOP_CONTRIBUTIONS,
        n_samples: int = EXPLANATION_SAMPLES,
    ) -> ExplainedPrediction:
        task, scenario = Task(task), Scenario(scenario)
        prediction = self.service.predict(cohort, task, scenario, record, model)
        meta, pipeline, data = self._context(cohort, task, scenario, model)
        raw = validated_record(record, scenario).iloc[0]
        background = data.train[list(attributes(scenario))]
        output = model_output(pipeline, task)
        estimate = shapley_values(
            output, raw, background, scenario, n_samples=n_samples, seed=DEFAULT_SEED
        )

        contributions = []
        for name, value, se in zip(
            estimate.attributes, estimate.values, estimate.standard_errors, strict=True
        ):
            negligible = abs(value) <= 2 * se or abs(value) < 1e-9
            contributions.append(
                Contribution(
                    attribute=name,
                    label=attribute_label(name),
                    value=value_label(name, raw[name]),
                    contribution=float(value),
                    standard_error=float(se),
                    direction="negligible" if negligible else ("raises" if value > 0 else "lowers"),
                )
            )
        contributions.sort(key=lambda c: -abs(c.contribution))
        shown, rest = contributions[:top], contributions[top:]
        target = output_label(task, meta.score_kind)
        towards = "a higher predicted grade" if task is Task.REGRESSION else "academic risk"

        percentile = None
        if task is Task.CLASSIFICATION:
            scores = self._training_scores(meta, pipeline, data)
            percentile = float(100 * np.mean(scores < estimate.prediction))

        return ExplainedPrediction(
            prediction=prediction,
            explanation=Explanation(
                method=(
                    "Interventional Shapley values estimated by permutation sampling over the "
                    "original attributes (antithetic sampling, fixed seed)"
                ),
                output=target,
                base_value=estimate.base_value,
                prediction=estimate.prediction,
                contributions=shown,
                other_attributes=len(rest),
                other_contribution=float(sum(c.contribution for c in rest)),
                n_samples=estimate.n_samples,
                background=f"training students of this cohort (n = {len(background)})",
                background_size=estimate.background_size,
                seed=DEFAULT_SEED,
                reading=(
                    f"The average {target} over training students is "
                    f"{estimate.base_value:.3f}. For this record the model gives "
                    f"{estimate.prediction:.3f}. Positive contributions moved the model "
                    f"towards {towards}, negative ones away from it; together they account "
                    "for the whole difference."
                ),
                limitations=EXPLANATION_LIMITATIONS,
            ),
            score_percentile=percentile,
        )

    def sensitivity(
        self,
        cohort: Cohort,
        task: Task,
        scenario: Scenario,
        record: Mapping[str, Any],
        attribute: str,
        model: str | None = None,
    ) -> SensitivityCurve:
        task, scenario = Task(task), Scenario(scenario)
        if attribute not in SENSITIVITY_ATTRIBUTES:
            raise InvalidRecordError(
                f"Sensitivity is available for {', '.join(SENSITIVITY_ATTRIBUTES)}; "
                f"not for {attribute!r}."
            )
        raw = validated_record(record, scenario)
        meta, pipeline, data = self._context(cohort, task, scenario, model)
        observed = data.train[attribute]
        current = raw[attribute].iloc[0]

        if attribute == "absences":
            maximum = int(observed.max())
            values = sorted({v for v in ABSENCE_GRID if v <= maximum} | {int(current)})
        else:
            values = [v.code for v in COLUMNS_BY_NAME[attribute].allowed]
            if isinstance(current, float):
                values = [float(v) for v in values]

        rows = pd.concat([raw] * len(values), ignore_index=True)
        rows[attribute] = pd.Series(values, dtype=raw[attribute].dtype)
        X = model_input(rows, scenario)
        outputs = model_output(pipeline, task)(X)
        labels = pipeline.predict(X) if task is Task.CLASSIFICATION else None

        points = []
        for i, value in enumerate(values):
            support = _support(observed, attribute, value)
            output = float(outputs[i])
            points.append(
                SensitivityPoint(
                    value=str(int(value) if isinstance(value, float) else value),
                    label=value_label(attribute, value),
                    current=value == current,
                    output=output,
                    predicted_grade=(
                        min(max(output, GRADE_MIN), GRADE_MAX) if task is Task.REGRESSION else None
                    ),
                    at_risk=bool(labels[i] == 1) if labels is not None else None,
                    support=support,
                    sparse=support < MIN_GROUP_SIZE,
                )
            )
        return SensitivityCurve(
            cohort=meta.cohort,
            task=task,
            scenario=scenario,
            model=meta.model,
            attribute=attribute,
            label=attribute_label(attribute),
            output=output_label(task, meta.score_kind),
            points=points,
            note=SENSITIVITY_NOTE + (_absence_note(data) if attribute == "absences" else ""),
        )

    def scenario_sensitivity(
        self, cohort: Cohort, task: Task, record: Mapping[str, Any]
    ) -> ScenarioSensitivity:
        task = Task(task)
        if leaked := set(record) & TARGET_COLUMNS:
            raise LeakageError(f"Outcome columns cannot be inputs: {sorted(leaked)}.")
        if unknown := set(record) - set(attributes(Scenario.FULL_HISTORY)):
            raise InvalidRecordError(f"Unknown attributes: {sorted(unknown)}.")
        items, skipped = [], []
        for scenario in (Scenario.EARLY, Scenario.MID_YEAR, Scenario.FULL_HISTORY):
            allowed = set(attributes(scenario))
            if not set(SCENARIOS[scenario].prior_grades) <= set(record):
                skipped.append(str(scenario))
                continue
            sub = {k: v for k, v in record.items() if k in allowed}
            result = self.service.predict(cohort, task, scenario, sub)
            items.append(
                ScenarioPrediction(
                    scenario=scenario,
                    model=result.model,
                    model_label=result.model_label,
                    output=result.raw_prediction if task is Task.REGRESSION else result.score,
                    predicted_grade=result.predicted_grade,
                    at_risk=result.at_risk,
                )
            )
        return ScenarioSensitivity(
            cohort=str(cohort),
            task=task,
            items=items,
            skipped=skipped,
            note=(
                "Each scenario uses its own selected model and only the information it allows. "
                "Differences reflect what is known at each point in the year (G1, G2), not a "
                "more accurate view of the student. Decision scores from different models are "
                "not on a common scale."
            ),
        )


def _absence_note(data: CohortData) -> str:
    note = (
        " Support for absences counts training students in the same band "
        "(0, 1–5, 6–10, 11–20, 21+)."
    )
    if data.zero_grades:
        note += (
            f" In the training data, {data.zero_grades_without_absences} of the "
            f"{data.zero_grades} students with G3 = 0 have 0 recorded absences, so a model "
            "can associate 0 absences with a final grade of 0. A change in output at 0 "
            "absences may reflect that pattern rather than attendance."
        )
    return note


def _support(observed: pd.Series, attribute: str, value) -> int:
    if attribute == "absences":
        for low, high in ABSENCE_BANDS:
            if low <= value <= high:
                return int(((observed >= low) & (observed <= high)).sum())
        return int((observed > ABSENCE_BANDS[-1][1]).sum())
    return int((observed == value).sum())
