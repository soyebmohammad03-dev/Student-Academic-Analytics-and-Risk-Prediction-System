"""Research questions and their pre-specified primary analyses.

Confirmatory family: one primary test per question (RQ1–RQ6, seven tests), fixed
before looking at results. Holm–Bonferroni controls the family-wise error rate at
α = 0.05 within each cohort.

Exploratory: RQ7 and RQ8, and every supporting analysis elsewhere, are
hypothesis-generating. They are corrected with Benjamini–Hochberg (false discovery
rate) and reported as such.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from analytics.statistics.association import associations
from analytics.statistics.comparisons import compare_groups
from analytics.statistics.config import ALPHA
from analytics.statistics.core import finite, holm, label_correlation
from analytics.statistics.correlation import correlate, spearman_matrix
from analytics.statistics.models import (
    Correlation,
    EffectSize,
    GroupComparison,
    ResearchQuestion,
    ResearchQuestions,
)


@dataclass(frozen=True)
class Question:
    key: str
    question: str
    h0: str
    h1: str
    analysis: str
    run: Callable[[pd.DataFrame], Correlation | GroupComparison]


QUESTIONS: tuple[Question, ...] = (
    Question(
        "RQ1",
        "Is weekly study time associated with final performance (G3)?",
        "There is no monotonic association between study time and G3 (ρ = 0).",
        "There is a monotonic association between study time and G3 (ρ ≠ 0).",
        "Spearman correlation: study time is a 4-level ordinal code.",
        lambda d: correlate(d, "studytime", "G3"),
    ),
    Question(
        "RQ2",
        "Do students with previous class failures perform differently in G3?",
        "G3 does not differ between students with and without past failures.",
        "G3 differs between students with and without past failures.",
        "Two-group comparison (no failures vs 1 or more), test chosen by assumption checks.",
        lambda d: compare_groups(d, "has_past_failures"),
    ),
    Question(
        "RQ3",
        "Are school absences associated with final performance (G3)?",
        "There is no monotonic association between absences and G3 (ρ = 0).",
        "There is a monotonic association between absences and G3 (ρ ≠ 0).",
        "Spearman correlation: absences is a skewed count.",
        lambda d: correlate(d, "absences", "G3"),
    ),
    Question(
        "RQ4",
        "Do final grades differ between female and male students?",
        "The G3 distribution does not differ between female and male students.",
        "The G3 distribution differs between female and male students.",
        "Two-group comparison by sex, test chosen by assumption checks.",
        lambda d: compare_groups(d, "sex"),
    ),
    Question(
        "RQ5",
        "Is mother's education level associated with final performance?",
        "G3 does not differ across mother's education levels.",
        "G3 differs across at least two mother's education levels.",
        "Four-group comparison (levels 0–1 merged), ANOVA family or Kruskal–Wallis by "
        "assumption checks, with post-hoc tests if significant.",
        lambda d: compare_groups(d, "Medu"),
    ),
    Question(
        "RQ6a",
        "Is extra educational support from the school associated with final performance?",
        "G3 does not differ between students with and without school support.",
        "G3 differs between students with and without school support.",
        "Two-group comparison, test chosen by assumption checks.",
        lambda d: compare_groups(d, "schoolsup"),
    ),
    Question(
        "RQ6b",
        "Is family educational support associated with final performance?",
        "G3 does not differ between students with and without family support.",
        "G3 differs between students with and without family support.",
        "Two-group comparison, test chosen by assumption checks.",
        lambda d: compare_groups(d, "famsup"),
    ),
)


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "n/a"
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def _confirmatory(q: Question, result, p_adj: float) -> ResearchQuestion:
    significant = p_adj < ALPHA
    if isinstance(result, Correlation):
        effect = EffectSize(
            name="Spearman ρ" if result.method == "spearman" else "Pearson r",
            value=result.r,
            ci=result.r_ci,
            magnitude=result.strength,
        )
        test, statistic = f"{result.method.capitalize()} correlation", result.r
        detail = (
            f"ρ = {result.r:.2f} (95% CI {result.r_ci.low:.2f} to {result.r_ci.high:.2f}), "
            f"n = {result.n}, Holm-adjusted p {_fmt_p(p_adj)}"
        )
        name = result.x_label
    else:
        effect = result.effect_sizes[0] if result.effect_sizes else None
        test, statistic = result.test, result.statistic
        sizes = ", ".join(f"{g.label}: n = {g.n}, median {g.median:g}" for g in result.groups)
        es = f"{effect.name} = {effect.value:.2f}" if effect and effect.value is not None else ""
        if effect and effect.ci and effect.ci.low is not None:
            es += f" (95% CI {effect.ci.low:.2f} to {effect.ci.high:.2f})"
        detail = f"{result.test}, {es}; {sizes}; Holm-adjusted p {_fmt_p(p_adj)}"
        name = result.variable_label
    magnitude = effect.magnitude if effect else "unknown"
    if significant:
        finding = (
            f"{name} shows a statistically significant association with G3 ({detail}). "
            f"Effect size: {magnitude}. This describes an association in this cohort, "
            "not a causal effect."
        )
    else:
        finding = (
            f"{name}: no statistically significant association with G3 after correction "
            f"({detail}). "
            "This does not show the absence of any relationship; the data are insufficient "
            "to reject H0 at α = 0.05."
        )
    return ResearchQuestion(
        key=q.key,
        question=q.question,
        h0=q.h0,
        h1=q.h1,
        analysis=q.analysis,
        evidence="confirmatory",
        test=test,
        statistic=finite(statistic),
        p=result.p,
        p_adjusted=finite(p_adj),
        significant=bool(significant),
        effect=effect,
        finding=finding,
    )


def _sensitivity(q: Question, data: pd.DataFrame) -> str | None:
    """Re-run the primary analysis without G3 = 0 students. Exploratory, unadjusted."""
    nonzero = data[data["G3"] > 0]
    if len(nonzero) == len(data):
        return None
    result = q.run(nonzero)
    if isinstance(result, Correlation):
        stat = f"ρ = {result.r:.2f} (95% CI {result.r_ci.low:.2f} to {result.r_ci.high:.2f})"
    else:
        effect = result.effect_sizes[0] if result.effect_sizes else None
        stat = f"{result.test}, {effect.name} = {effect.value:.2f}" if effect else result.test
    return (
        f"Without the {len(data) - len(nonzero)} students with G3 = 0 (n = {len(nonzero)}): "
        f"{stat}, unadjusted p {_fmt_p(result.p)}. Exploratory sensitivity check only."
    )


def _strongest_numeric(data: pd.DataFrame) -> ResearchQuestion:
    matrix = spearman_matrix(data)
    g3 = matrix.variables.index("G3")
    ranked = sorted(
        (
            (matrix.variables[i], matrix.labels[i], matrix.r[g3][i], matrix.p_adjusted[g3][i])
            for i in range(len(matrix.variables))
            if i != g3
        ),
        key=lambda t: -abs(t[2] or 0),
    )
    non_grade = [t for t in ranked if t[0] not in {"G1", "G2"}][:3]
    top = ranked[0]
    text = "; ".join(
        f"{label} ρ = {r:.2f} (BH-adjusted p {_fmt_p(p)})" for _, label, r, p in ranked[:2]
    )
    text_ng = "; ".join(
        f"{label} ρ = {r:.2f} (BH-adjusted p {_fmt_p(p)})" for _, label, r, p in non_grade
    )
    return ResearchQuestion(
        key="RQ7",
        question="Which numerical variables show the strongest relationships with G3?",
        h0="—",
        h1="—",
        analysis=(
            "Exploratory ranking of |Spearman ρ| with G3 across 15 numeric variables; "
            "Benjamini–Hochberg across the matrix."
        ),
        evidence="exploratory",
        test="Spearman correlation matrix",
        statistic=top[2],
        p=None,
        p_adjusted=top[3],
        significant=bool(top[3] is not None and top[3] < ALPHA),
        effect=EffectSize(
            name=f"Spearman ρ ({top[1]})", value=top[2], magnitude=label_correlation(top[2])
        ),
        finding=(
            f"Interim grades are the strongest correlates of G3: {text}. Among non-grade "
            f"variables the strongest are: {text_ng}. Rankings are exploratory and describe "
            "association only."
        ),
    )


def _categorical_risk(data: pd.DataFrame, cohort: str) -> ResearchQuestion:
    result = associations(data, cohort)
    significant = sorted(
        (a for a in result.items if a.p_adjusted is not None and a.p_adjusted < ALPHA),
        key=lambda a: -(a.cramers_v or 0),
    )
    listed = "; ".join(
        f"{a.label} (V = {a.cramers_v:.2f}, {a.magnitude}, BH-adjusted p {_fmt_p(a.p_adjusted)})"
        for a in significant
    )
    best = significant[0] if significant else None
    return ResearchQuestion(
        key="RQ8",
        question="Which categorical variables show meaningful associations with academic risk?",
        h0="Each variable is independent of at_risk.",
        h1="The variable is associated with at_risk.",
        analysis=(
            f"Chi-square tests (Fisher's exact where needed) for {len(result.items)} variables; "
            f"Cramér's V; Benjamini–Hochberg."
        ),
        evidence="exploratory",
        test="Chi-square test of independence",
        statistic=best.statistic if best else None,
        p=best.p if best else None,
        p_adjusted=best.p_adjusted if best else None,
        significant=bool(best),
        effect=EffectSize(
            name=f"Cramér's V ({best.label})", value=best.cramers_v, magnitude=best.magnitude
        )
        if best
        else None,
        finding=(
            (
                f"Associated with academic risk after FDR control: {listed}. These are "
                f"exploratory associations."
            )
            if significant
            else (
                "No categorical variable shows a significant association with academic risk "
                "after FDR control."
            )
        ),
    )


def research_questions(data: pd.DataFrame, cohort: str) -> ResearchQuestions:
    results = [(q, q.run(data)) for q in QUESTIONS]
    adjusted = holm([r.p for _, r in results])
    items = [_confirmatory(q, r, p) for (q, r), p in zip(results, adjusted, strict=True)]
    for item, q in zip(items, QUESTIONS, strict=True):
        item.sensitivity = _sensitivity(q, data)
    items += [_strongest_numeric(data), _categorical_risk(data, cohort)]
    return ResearchQuestions(
        cohort=cohort,
        alpha=ALPHA,
        correction=(
            "Holm–Bonferroni across the seven confirmatory tests (RQ1–RQ6b); Benjamini–Hochberg "
            "within exploratory analyses (RQ7, RQ8)."
        ),
        items=items,
    )
