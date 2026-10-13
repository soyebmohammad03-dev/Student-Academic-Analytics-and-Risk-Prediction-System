"""Error analysis of the selected models on the held-out test set.

Students are referred to only by their 1-based row position in the source file. The
dataset contains no names or identifiers, and no attribute values are reported.
Pattern notes are generated from the numbers below them; thresholds for mentioning a
pattern are fixed here, not chosen after looking at the results.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd

from analytics.ml.evaluation import Predictions
from analytics.ml.metrics import classification_metrics, confusion, regression_metrics
from analytics.ml.results import (
    ClassificationErrors,
    ClassOutcome,
    Confusion,
    GradeBand,
    GradeCount,
    LargeError,
    RegressionErrors,
    ResidualBin,
    ResidualSummary,
)
from analytics.preprocessing import RISK_THRESHOLD, Scenario

#: Grade bands for residual patterns. The first isolates G3 = 0 (see Phase 4).
GRADE_BANDS: tuple[tuple[str, int, int], ...] = (
    ("G3 = 0", 0, 0),
    (f"G3 1–{RISK_THRESHOLD - 1} (below pass mark)", 1, RISK_THRESHOLD - 1),
    (f"G3 {RISK_THRESHOLD}–14", RISK_THRESHOLD, 14),
    ("G3 15–20", 15, 20),
)
LARGEST_ERRORS = 10
#: A band's mean residual is called systematic when at least this large (grade points)
#: and the band has at least MIN_BAND students.
SYSTEMATIC_BIAS = 1.0
MIN_BAND = 5


def _row(index) -> int:
    return int(index) + 1


def regression_errors(
    cohort: str, scenario: Scenario, model: str, p: Predictions
) -> RegressionErrors:
    actual, predicted = p.y_true.astype(float), p.y_pred.astype(float)
    residual = actual - predicted
    absolute = np.abs(residual)

    low, high = math.floor(residual.min()), math.ceil(residual.max())
    high = max(high, low + 1)
    edges = np.arange(low, high + 1)
    counts, _ = np.histogram(residual, bins=edges)
    histogram = [
        ResidualBin(start=float(a), end=float(b), label=f"{a:+d} to {b:+d}", count=int(c))
        for a, b, c in zip(edges[:-1], edges[1:], counts, strict=True)
    ]

    bands, patterns = [], []
    for label, lo, hi in GRADE_BANDS:
        mask = (actual >= lo) & (actual <= hi)
        n = int(mask.sum())
        mae = float(absolute[mask].mean()) if n else None
        bias = float(residual[mask].mean()) if n else None
        bands.append(GradeBand(band=label, n=n, mae=mae, mean_residual=bias))
        if n >= MIN_BAND and bias is not None and abs(bias) >= SYSTEMATIC_BIAS:
            direction = "under-predicted" if bias > 0 else "over-predicted"
            patterns.append(
                f"Students with {label} are {direction} by {abs(bias):.1f} grade points on "
                f"average (n = {n}, MAE {mae:.1f})."
            )
    zero = actual == 0
    zero_reported = bands[0].n >= MIN_BAND and abs(bands[0].mean_residual or 0) >= SYSTEMATIC_BIAS
    if zero.any() and not zero_reported:
        patterns.append(
            f"For the {int(zero.sum())} test students with G3 = 0 the model predicts "
            f"{predicted[zero].mean():.1f} on average."
        )
    if not patterns:
        patterns.append(
            f"No grade band has a mean residual of {SYSTEMATIC_BIAS:g} grade point or more."
        )

    order = np.argsort(-absolute, kind="stable")[:LARGEST_ERRORS]
    return RegressionErrors(
        cohort=cohort,
        scenario=scenario,
        model=model,
        n=len(actual),
        metrics=regression_metrics(actual, predicted),
        residuals=ResidualSummary(
            mean=float(residual.mean()),
            std=float(residual.std(ddof=1)) if len(residual) > 1 else None,
            median=float(np.median(residual)),
            q1=float(np.percentile(residual, 25)),
            q3=float(np.percentile(residual, 75)),
            min=float(residual.min()),
            max=float(residual.max()),
            within_1=float((absolute <= 1).mean()),
            within_2=float((absolute <= 2).mean()),
        ),
        histogram=histogram,
        by_band=bands,
        largest=[
            LargeError(
                row=_row(p.index[i]),
                actual=float(actual[i]),
                predicted=float(predicted[i]),
                residual=float(residual[i]),
            )
            for i in order
        ],
        patterns=patterns,
    )


def _grade_counts(grades: pd.Series) -> list[GradeCount]:
    return [GradeCount(grade=int(g), count=c) for g, c in sorted(Counter(grades).items())]


def classification_errors(
    cohort: str,
    scenario: Scenario,
    model: str,
    p: Predictions,
    grades: pd.Series,
    *,
    threshold: float,
    score_kind: str,
) -> ClassificationErrors:
    grades = grades.loc[p.index].astype(int)
    actual, predicted = p.y_true.astype(int), p.y_pred.astype(int)
    c = Confusion(**confusion(actual, predicted))
    fn = grades[(actual == 1) & (predicted == 0)]
    fp = grades[(actual == 0) & (predicted == 1)]
    zero = (grades == 0).to_numpy()

    def outcome(label: str, cls: int) -> ClassOutcome:
        n = int((actual == cls).sum())
        correct = int(((actual == cls) & (predicted == cls)).sum())
        return ClassOutcome(label=label, n=n, correct=correct, rate=correct / n if n else None)

    patterns = []
    if len(fn):
        near = int((fn >= RISK_THRESHOLD - 2).sum())
        patterns.append(
            f"{len(fn)} at-risk student(s) were missed; {near} of them had a final grade of "
            f"{RISK_THRESHOLD - 2} or {RISK_THRESHOLD - 1}, just below the pass mark."
        )
    else:
        patterns.append("No at-risk student in the test set was missed.")
    if len(fp):
        near = int((fp <= RISK_THRESHOLD + 1).sum())
        patterns.append(
            f"{len(fp)} student(s) who passed were flagged; {near} of them had a final grade of "
            f"{RISK_THRESHOLD} or {RISK_THRESHOLD + 1}, just above the pass mark."
        )
    if zero.any():
        patterns.append(
            f"{int((predicted[zero] == 1).sum())} of {int(zero.sum())} test students with G3 = 0 "
            "were flagged as at risk."
        )

    return ClassificationErrors(
        cohort=cohort,
        scenario=scenario,
        model=model,
        n=len(actual),
        threshold=threshold,
        score_kind=score_kind,
        confusion=c,
        metrics=classification_metrics(actual, predicted, p.scores),
        by_class=[outcome("At risk", 1), outcome("Not at risk", 0)],
        false_negative_grades=_grade_counts(fn),
        false_positive_grades=_grade_counts(fp),
        zero_grade_detected=int((predicted[zero] == 1).sum()),
        zero_grade_total=int(zero.sum()),
        patterns=patterns,
    )
