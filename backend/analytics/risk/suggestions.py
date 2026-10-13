"""Cautious, evidence-checked suggestions for human review.

Each rule is triggered by an observable input and is shown only when this cohort's
data support it: the triggering group must have a higher observed academic-risk
proportion than the remaining students (Fisher's exact test, two-sided, unadjusted
p < 0.05; exploratory). A rule triggered by a model flag is supported by the selected
model's held-out recall and precision instead.

Wording rules (checked by tests): suggestions are addressed to a teacher or adviser,
phrased as something to consider, never punitive or disciplinary, never clinical,
psychological or family judgements, and never claim that changing an attribute will
change a grade. Demographic and family-background attributes never trigger a rule.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd
from scipy import stats

from analytics.ml.predict import PredictionResult
from analytics.preprocessing import RISK_LABEL
from analytics.risk.results import Evidence, Suggestion, SuggestionSet
from analytics.statistics.config import ALPHA

DISCLAIMER = (
    "These are general suggestions for a teacher or adviser to consider together with the "
    "student. They are prompted by recorded information and group-level patterns in a "
    "historical dataset, not by knowledge of this student. They are not diagnoses or "
    "instructions, must not be used for disciplinary decisions, and do not imply that "
    "changing any single factor will change a grade."
)


@dataclass(frozen=True)
class Rule:
    key: str
    text: str
    trigger_text: str
    applies: Callable[[Mapping[str, Any]], bool]
    #: Same condition, applied to the cohort's students (for the evidence check).
    group: Callable[[pd.DataFrame], pd.Series]
    group_label: str
    rest_label: str


RULES: tuple[Rule, ...] = (
    Rule(
        key="past_difficulties",
        text=(
            "Consider discussing earlier academic difficulties with the student and an "
            "adviser, to understand what support has or has not helped before."
        ),
        trigger_text="One or more past class failures recorded.",
        applies=lambda r: int(r["failures"]) >= 1,
        group=lambda d: d["failures"] >= 1,
        group_label="students with past failures",
        rest_label="students without past failures",
    ),
    Rule(
        key="study_routine",
        text=(
            "Consider reviewing study routines with the student, for example when and how "
            "they study outside class."
        ),
        trigger_text="Weekly study time recorded as less than 2 hours.",
        applies=lambda r: int(r["studytime"]) == 1,
        group=lambda d: d["studytime"] == 1,
        group_label="students studying less than 2 hours a week",
        rest_label="students studying 2 hours or more",
    ),
    Rule(
        key="attendance",
        text=(
            "Consider looking at attendance patterns together with the student, to "
            "understand whether anything is making it harder to attend."
        ),
        trigger_text="More than 10 school absences recorded.",
        applies=lambda r: int(r["absences"]) > 10,
        group=lambda d: d["absences"] > 10,
        group_label="students with more than 10 absences",
        rest_label="students with 10 or fewer absences",
    ),
)

MODEL_FLAG_TEXT = (
    "Consider a supportive check-in about how the course is going, and whether additional "
    "learning support would be useful."
)


def _evidence(rule: Rule, data: pd.DataFrame) -> Evidence:
    risk = data[RISK_LABEL].astype(int)
    in_group = rule.group(data).astype(bool)
    g, r = risk[in_group], risk[~in_group]
    if len(g) == 0 or len(r) == 0:
        return Evidence(
            kind="group_statistics",
            summary=f"Not enough students to compare {rule.group_label} with the others.",
            supported=False,
        )
    table = [[int(g.sum()), len(g) - int(g.sum())], [int(r.sum()), len(r) - int(r.sum())]]
    _, p = stats.fisher_exact(table)
    gp, rp = 100 * g.mean(), 100 * r.mean()
    supported = bool(gp > rp and p < ALPHA)
    summary = (
        f"In this cohort, {gp:.0f}% of {rule.group_label} (n = {len(g)}) had a final grade "
        f"below the pass mark, compared with {rp:.0f}% of {rule.rest_label} (n = {len(r)}); "
        f"Fisher's exact p = {p:.3g}."
    )
    if not supported:
        summary += " The data do not show a clearly higher risk for this group, so it is not shown."
    return Evidence(
        kind="group_statistics",
        summary=summary,
        group_n=len(g),
        group_risk_percent=float(gp),
        comparison_n=len(r),
        comparison_risk_percent=float(rp),
        p=float(p),
        supported=supported,
    )


def suggest(
    data: pd.DataFrame,
    cohort: str,
    record: Mapping[str, Any],
    flag: PredictionResult | None = None,
) -> SuggestionSet:
    """``record`` must already be validated; ``flag`` is a classification prediction."""
    shown, hidden = [], []
    for rule in RULES:
        if not rule.applies(record):
            continue
        evidence = _evidence(rule, data)
        item = Suggestion(
            key=rule.key, text=rule.text, trigger=rule.trigger_text, evidence=evidence
        )
        (shown if evidence.supported else hidden).append(item)

    if flag is not None and flag.at_risk:
        recall = flag.model_test_metrics.get("recall") or 0.0
        precision = flag.model_test_metrics.get("precision") or 0.0
        shown.append(
            Suggestion(
                key="model_flag",
                text=MODEL_FLAG_TEXT,
                trigger=(
                    f"The selected {flag.model_label.lower()} model ({flag.scenario} scenario) "
                    "flagged this record as at academic risk."
                ),
                evidence=Evidence(
                    kind="model_performance",
                    summary=(
                        f"On held-out students this model identified {100 * recall:.0f}% of "
                        f"those who fell below the pass mark, and {100 * precision:.0f}% of "
                        "the students it flagged did fall below it. A flag is a statistical "
                        "estimate and can be wrong for any individual."
                    ),
                    supported=True,
                ),
            )
        )
    return SuggestionSet(cohort=cohort, suggestions=shown, not_shown=hidden, disclaimer=DISCLAIMER)
