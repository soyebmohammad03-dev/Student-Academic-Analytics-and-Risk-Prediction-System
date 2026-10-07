"""Distributions of G1, G2 and G3, and the academic-risk proportion."""

from __future__ import annotations

import pandas as pd
from scipy import stats

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.preprocessing import RISK_LABEL, RISK_THRESHOLD
from analytics.statistics.config import ALPHA
from analytics.statistics.core import finite, wilson_ci
from analytics.statistics.descriptive import numeric_summary
from analytics.statistics.models import (
    Distributions,
    GradeDistribution,
    Interval,
    RiskSummary,
    Shape,
    ValueCount,
)

GRADES = ("G1", "G2", "G3")


def _shape(values: pd.Series) -> Shape:
    x = values.astype(float).to_numpy()
    skew = float(stats.skew(x, bias=False))
    kurt = float(stats.kurtosis(x, bias=False))
    w, p = stats.shapiro(x)
    side = "left-skewed" if skew < -0.5 else "right-skewed" if skew > 0.5 else "roughly symmetric"
    tails = (
        "heavier-tailed than normal"
        if kurt > 1
        else "lighter-tailed than normal"
        if kurt < -1
        else "near-normal tails"
    )
    verdict = "normality rejected" if p < ALPHA else "normality not rejected"
    return Shape(
        skewness=finite(skew),
        kurtosis=finite(kurt),
        shapiro_w=finite(w),
        shapiro_p=finite(p),
        normality_rejected=bool(p < ALPHA),
        description=f"{side.capitalize()}, {tails} (Shapiro–Wilk: {verdict} at α = {ALPHA}).",
    )


def grade_distribution(data: pd.DataFrame, name: str) -> GradeDistribution:
    values = data[name].astype("int64")
    counts = values.value_counts()
    nonzero = values[values > 0]
    return GradeDistribution(
        variable=name,
        label=COLUMNS_BY_NAME[name].label,
        summary=numeric_summary(values, name),
        counts=[ValueCount(value=g, count=int(counts.get(g, 0))) for g in range(0, 21)],
        zero_count=int((values == 0).sum()),
        shape=_shape(values),
        summary_excluding_zeros=(
            numeric_summary(nonzero, name, f"{COLUMNS_BY_NAME[name].label} (excluding 0)")
            if len(nonzero) < len(values) and len(nonzero) > 1
            else None
        ),
    )


def risk_summary(data: pd.DataFrame) -> RiskSummary:
    at_risk = int(data[RISK_LABEL].sum())
    n = len(data)
    low, high = wilson_ci(at_risk, n)
    return RiskSummary(
        threshold=RISK_THRESHOLD,
        n=n,
        at_risk=at_risk,
        proportion=at_risk / n,
        proportion_ci=Interval(low=finite(low), high=finite(high)),
        zero_grade_at_risk=int(((data["G3"] == 0) & (data[RISK_LABEL] == 1)).sum()),
    )


def zero_grade_observations(data: pd.DataFrame) -> list[str]:
    zero = data[data["G3"] == 0]
    if zero.empty:
        return []
    n = len(zero)
    notes = [
        f"{n} students ({100 * n / len(data):.1f}%) have a final grade of 0. They are kept in "
        "every analysis and are all at risk by definition."
    ]
    no_absences = int((zero["absences"] == 0).sum())
    notes.append(
        f"{no_absences} of these {n} students have 0 recorded absences, compared with "
        f"{100 * (data.loc[data['G3'] > 0, 'absences'] == 0).mean():.1f}% of students with "
        "G3 > 0. This pattern suggests that some zero grades may reflect a missed final "
        "evaluation rather than low attainment; the data cannot confirm this."
    )
    g2_zero = int((zero["G2"] == 0).sum())
    notes.append(f"{g2_zero} of the {n} also have G2 = 0.")
    return notes


def distributions(data: pd.DataFrame, cohort: str) -> Distributions:
    return Distributions(
        cohort=cohort,
        grades=[grade_distribution(data, g) for g in GRADES],
        risk=risk_summary(data),
        observations=zero_grade_observations(data),
    )
