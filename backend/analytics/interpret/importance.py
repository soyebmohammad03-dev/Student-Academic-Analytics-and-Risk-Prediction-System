"""Global feature importance for the selected (persisted) models.

Four methods, each reported separately with its own unit. They answer different
questions and their values are **never** compared with each other:

- ``permutation_test`` — every model. Drop in held-out performance when one
  attribute's values are shuffled among test students (RMSE increase for regression,
  ROC-AUC decrease for classification). An *evaluation-time diagnostic*: the test set
  is only scored, never used for fitting.
- ``mean_abs_shapley`` — every model. Mean absolute Shapley contribution to the model
  output over the test students (labels not used). Describes model behaviour.
- ``impurity_decrease`` — tree and forest models only. Mean decrease in impurity from
  fitting on the training set, summed over an attribute's encoded columns.
- ``standardised_coefficient`` — linear and logistic models only. Coefficients per
  encoded feature on the standardised scale.

All work on the persisted pipelines; nothing is retrained.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from analytics.interpret.attributes import (
    attribute_label,
    attributes,
    encoded_attribute,
    model_input,
)
from analytics.interpret.results import (
    Calibration,
    CalibrationBin,
    ImportanceItem,
    ImportanceResult,
)
from analytics.interpret.shapley import shapley_values
from analytics.ml.config import Task
from analytics.ml.metrics import positive_scores, roc_auc
from analytics.ml.results import ArtifactMetadata
from analytics.preprocessing.pipeline import column_groups

PERMUTATION_REPEATS = 30
GLOBAL_SHAPLEY_SAMPLES = 128
CALIBRATION_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

NOT_CAUSAL = (
    "Describes how the model uses its inputs. It is not evidence that the attribute "
    "causes, or that changing it would change, a student's grade."
)


def model_output(pipeline, task: Task) -> Callable[[pd.DataFrame], np.ndarray]:
    if Task(task) is Task.REGRESSION:
        return lambda X: np.asarray(pipeline.predict(X), dtype=float)
    return lambda X: positive_scores(pipeline, X)


def output_label(task: Task, score_kind: str | None) -> str:
    if Task(task) is Task.REGRESSION:
        return "predicted final grade G3 (grade points)"
    if score_kind == "probability":
        return "model probability of academic risk (class-weighted, not calibrated)"
    return "SVM decision score for academic risk (not a probability)"


def _ranked(rows: list[tuple[str, str, str, float, float | None]]) -> list[ImportanceItem]:
    rows = sorted(rows, key=lambda r: -abs(r[3]))
    return [
        ImportanceItem(feature=f, attribute=a, label=lbl, value=v, std=s, rank=i + 1)
        for i, (f, a, lbl, v, s) in enumerate(rows)
    ]


def _result(meta: ArtifactMetadata, method, label, data, unit, items, limitations):
    return ImportanceResult(
        cohort=meta.cohort,
        task=meta.task,
        scenario=meta.scenario,
        model=meta.model,
        model_label=meta.label,
        method=method,
        method_label=label,
        data=data,
        unit=unit,
        items=items,
        limitations=limitations,
    )


def _performance(task: Task, y: np.ndarray, out: np.ndarray) -> float:
    if Task(task) is Task.REGRESSION:
        return float(np.sqrt(np.mean((y - out) ** 2)))
    return roc_auc(y, out)


def permutation_importance(
    meta: ArtifactMetadata,
    pipeline,
    raw_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    repeats: int = PERMUTATION_REPEATS,
    seed: int = 42,
    subset: str | None = None,
) -> ImportanceResult:
    """``subset`` labels a restricted test set (e.g. the G3 > 0 sensitivity check)."""
    task, scenario = meta.task, meta.scenario
    names = attributes(scenario)
    output = model_output(pipeline, task)
    y = y_test.to_numpy(dtype=float)
    base = _performance(task, y, output(model_input(raw_test, scenario)))

    rng = np.random.default_rng(seed)
    n = len(raw_test)
    blocks = []
    for name in names:
        for _ in range(repeats):
            block = raw_test.copy()
            block[name] = raw_test[name].to_numpy()[rng.permutation(n)]
            blocks.append(block)
    outputs = output(model_input(pd.concat(blocks, ignore_index=True), scenario))
    outputs = outputs.reshape(len(names), repeats, n)

    rows = []
    for i, name in enumerate(names):
        scores = np.array([_performance(task, y, outputs[i, r]) for r in range(repeats)])
        drops = scores - base if task is Task.REGRESSION else base - scores
        rows.append(
            (name, name, attribute_label(name), float(drops.mean()), float(drops.std(ddof=1)))
        )
    unit = "increase in test RMSE" if task is Task.REGRESSION else "decrease in test ROC-AUC"
    return _result(
        meta,
        "permutation_test",
        "Permutation importance (held-out test set)"
        if subset is None
        else f"Permutation importance (test set, {subset})",
        f"Test set{'' if subset is None else ' restricted to ' + subset}, n = {n}; "
        f"{repeats} shuffles per attribute; baseline "
        f"{'RMSE' if task is Task.REGRESSION else 'ROC-AUC'} {base:.3f}.",
        unit,
        _ranked(rows),
        [
            "Evaluation-time diagnostic on the held-out test set; the test set is only "
            "scored, never used for fitting or tuning.",
            "Attributes that carry overlapping information share importance: shuffling "
            "one leaves the others intact, so a small value does not mean the attribute "
            "is unrelated to the outcome.",
            "The test set is small, so values are noisy; the SD over shuffles is shown. "
            "Values near 0 (or slightly negative) mean no measurable reliance.",
            NOT_CAUSAL,
        ],
    )


def mean_abs_shapley(
    meta: ArtifactMetadata,
    pipeline,
    raw_rows: pd.DataFrame,
    background: pd.DataFrame,
    *,
    n_samples: int = GLOBAL_SHAPLEY_SAMPLES,
    seed: int = 42,
) -> ImportanceResult:
    output = model_output(pipeline, meta.task)
    values = np.array(
        [
            shapley_values(
                output, row, background, meta.scenario, n_samples=n_samples, seed=seed + i
            ).values
            for i, (_, row) in enumerate(raw_rows.iterrows())
        ]
    )
    names = attributes(meta.scenario)
    magnitude = np.abs(values)
    rows = [
        (name, name, attribute_label(name), float(magnitude[:, i].mean()),
         float(magnitude[:, i].std(ddof=1)))
        for i, name in enumerate(names)
    ]  # fmt: skip
    return _result(
        meta,
        "mean_abs_shapley",
        "Mean absolute Shapley value",
        f"Explanations of the {len(raw_rows)} test students (labels not used); "
        f"{n_samples} permutation samples each; background = training set "
        f"({len(background)} students).",
        f"mean |contribution| to the {output_label(meta.task, meta.score_kind)}",
        _ranked(rows),
        [
            "Average size of an attribute's contribution to the model output, regardless "
            "of direction.",
            "Interventional Shapley values replace attributes with values from other "
            "students independently, which can create atypical combinations of inputs.",
            "Monte Carlo estimates: small differences between attributes are not meaningful.",
            NOT_CAUSAL,
        ],
    )


def impurity_importance(meta: ArtifactMetadata, pipeline) -> ImportanceResult | None:
    estimator = pipeline.named_steps["model"]
    if not hasattr(estimator, "feature_importances_"):
        return None
    totals: dict[str, float] = {}
    for name, value in zip(meta.encoded_features, estimator.feature_importances_, strict=True):
        attribute, _ = encoded_attribute(name)
        totals[attribute] = totals.get(attribute, 0.0) + float(value)
    rows = [(a, a, attribute_label(a), v, None) for a, v in totals.items()]
    return _result(
        meta,
        "impurity_decrease",
        "Impurity-based importance (training data)",
        f"Computed while fitting on the training set (n = {meta.n_train}).",
        "share of total impurity decrease (sums to 1)",
        _ranked(rows),
        [
            "Derived from training data, so it reflects what the model fitted, including "
            "any over-fitting.",
            "Biased towards attributes with many distinct values (grades, absences, age) "
            "and splits correlated attributes arbitrarily.",
            "Summed over an attribute's encoded columns.",
            NOT_CAUSAL,
        ],
    )


def coefficient_importance(meta: ArtifactMetadata, pipeline) -> ImportanceResult | None:
    estimator = pipeline.named_steps["model"]
    if not hasattr(estimator, "coef_"):
        return None
    coefficients = np.ravel(estimator.coef_)
    nominal = set(column_groups(meta.scenario)["nominal"])
    rows = []
    for name, value in zip(meta.encoded_features, coefficients, strict=True):
        attribute, label = encoded_attribute(name)
        rows.append((name, attribute, label, float(value), None))
    regression = meta.task is Task.REGRESSION
    unit = (
        "change in predicted G3 (grade points)"
        if regression
        else "change in log-odds of academic risk"
    ) + " per standard deviation (ordinal/numeric) or versus the reference category (binary)"
    limitations = [
        "Each coefficient is conditional on every other input being held fixed; inputs "
        "are correlated, so coefficients can differ in sign from simple associations.",
        "Ordinal codes are treated as equally spaced and standardised.",
    ]
    if regression:
        limitations.append(
            f"Nominal attributes ({', '.join(sorted(nominal))}) are fully one-hot encoded, so "
            "their coefficients are identified only relative to each other within the same "
            "attribute (minimum-norm least-squares solution)."
        )
    else:
        limitations.append(
            f"L2-regularised (C = {meta.best_params.get('C')}): coefficients are shrunk "
            "towards 0. For one-hot attributes compare categories within the attribute."
        )
    limitations.append(NOT_CAUSAL)
    return _result(
        meta,
        "standardised_coefficient",
        "Model coefficients",
        f"Fitted on the training set (n = {meta.n_train}).",
        unit,
        _ranked(rows),
        limitations,
    )


def calibration(meta: ArtifactMetadata, scores: np.ndarray, y: np.ndarray) -> Calibration | None:
    if meta.score_kind != "probability":
        return None
    bins = []
    edges = CALIBRATION_EDGES
    for i, (low, high) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        last = i == len(edges) - 2
        mask = (scores >= low) & ((scores <= high) if last else (scores < high))
        n = int(mask.sum())
        bins.append(
            CalibrationBin(
                low=low,
                high=high,
                n=n,
                mean_predicted=float(scores[mask].mean()) if n else None,
                observed_rate=float(y[mask].mean()) if n else None,
            )
        )
    return Calibration(
        cohort=meta.cohort,
        scenario=meta.scenario,
        model=meta.model,
        n=len(y),
        brier=float(np.mean((scores - y) ** 2)),
        mean_predicted=float(scores.mean()),
        observed_rate=float(y.mean()),
        bins=bins,
        note=(
            "Held-out test set. The model was trained with balanced class weights, which "
            "shifts probabilities towards the minority (at-risk) class. Here the mean "
            f"predicted probability is {scores.mean():.2f} against an observed rate of "
            f"{y.mean():.2f}"
            + (
                ", so probabilities overstate"
                if scores.mean() > y.mean()
                else ", so they understate"
            )
            + " how often students fall below the pass mark on average. They are useful for "
            "ordering students, not as calibrated chances. Bins with few students are unreliable."
        ),
    )
