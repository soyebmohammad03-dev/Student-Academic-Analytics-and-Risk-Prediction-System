"""Academic-risk profiles of observed student groups (group-level statistics).

Groups are defined in advance from school-related attributes: past failures, study
time, absences, school and family support, paid classes, plans for higher education
and internet access. Demographic attributes (sex, age, address, parents' jobs and
education) are deliberately not profiled here; their associations are reported with
the Phase 4 statistics, and labelling demographic groups as "high-risk" would
stigmatise them.

Every figure is an observed proportion of students below the pass mark in this
dataset, with a 95% Wilson interval. It describes groups, not any individual.
"""

from __future__ import annotations

import pandas as pd

from analytics.preprocessing import RISK_LABEL, RISK_THRESHOLD
from analytics.risk.results import (
    PairCell,
    PairProfile,
    ProfileGroup,
    RiskProfiles,
    SingleProfile,
)
from analytics.statistics.association import associate
from analytics.statistics.config import MIN_GROUP_SIZE
from analytics.statistics.core import benjamini_hochberg, finite, wilson_ci
from analytics.statistics.groups import GROUPINGS
from analytics.statistics.models import Interval

PROFILE_VARIABLES: tuple[str, ...] = (
    "failures",
    "studytime",
    "absence_band",
    "schoolsup",
    "famsup",
    "paid",
    "higher",
    "internet",
)
PROFILE_PAIRS: tuple[tuple[str, str], ...] = (
    ("has_past_failures", "studytime"),
    ("has_past_failures", "absence_band"),
    ("has_past_failures", "schoolsup"),
)

NOTES = [
    "Observed proportions of students with a final grade below the pass mark in this "
    "dataset. They describe groups, not any individual student, and are not causal.",
    "Groups with fewer than 10 students are marked unreliable; their intervals are wide.",
]


def _data_notes(data: pd.DataFrame) -> list[str]:
    """Notes whose content depends on the data are generated from it."""
    notes = []
    risk = data[RISK_LABEL].astype(int)
    support = data["schoolsup"] == "yes"
    if support.any() and (~support).any() and risk[support].mean() > risk[~support].mean():
        notes.append(
            f"Students receiving extra school support have a higher observed risk "
            f"({100 * risk[support].mean():.0f}% vs {100 * risk[~support].mean():.0f}%). "
            "Support is usually given to students who are already struggling, so this does "
            "not show that support is ineffective."
        )
    zero = data["G3"] == 0
    if zero.any():
        no_absence = int((data.loc[zero, "absences"] == 0).sum())
        notes.append(
            f"{no_absence} of the {int(zero.sum())} students with G3 = 0 have 0 recorded "
            "absences. A G3 of 0 may mean the final evaluation was not taken, and these "
            "students raise the observed risk of the no-absence group."
        )
    return notes


def _interval(at: int, n: int) -> Interval:
    low, high = wilson_ci(at, n) if n else (None, None)
    return Interval(low=finite(low), high=finite(high))


def risk_profiles(data: pd.DataFrame, cohort: str) -> RiskProfiles:
    risk = data[RISK_LABEL].astype(int)
    n, at = len(risk), int(risk.sum())
    overall = 100 * at / n

    single = []
    for variable in PROFILE_VARIABLES:
        a = associate(data, variable)
        single.append(
            SingleProfile(
                variable=variable,
                label=a.label,
                groups=[
                    ProfileGroup(
                        key=r.category,
                        label=r.label,
                        n=r.n,
                        at_risk=r.at_risk,
                        risk_percent=r.risk_percent,
                        risk_ci=r.risk_ci,
                        difference_from_overall=r.risk_percent - overall,
                        reliable=r.n >= MIN_GROUP_SIZE,
                    )
                    for r in a.rows
                ],
                test=a.test,
                p=a.p,
                p_adjusted=None,
                cramers_v=a.cramers_v,
                magnitude=a.magnitude,
                warnings=a.warnings,
            )
        )
    adjusted = benjamini_hochberg([s.p for s in single])
    for item, p in zip(single, adjusted, strict=True):
        item.p_adjusted = finite(p)

    pairs = []
    for rows_var, cols_var in PROFILE_PAIRS:
        rg, cg = GROUPINGS[rows_var], GROUPINGS[cols_var]
        rk, ck = rg.assign(data), cg.assign(data)
        cells = []
        for r_key, r_label in rg.levels:
            for c_key, c_label in cg.levels:
                mask = (rk == r_key) & (ck == c_key)
                cn, ca = int(mask.sum()), int(risk[mask].sum())
                cells.append(
                    PairCell(
                        row=r_key,
                        row_label=r_label,
                        column=c_key,
                        column_label=c_label,
                        n=cn,
                        at_risk=ca,
                        risk_percent=100 * ca / cn if cn else None,
                        risk_ci=_interval(ca, cn),
                        reliable=cn >= MIN_GROUP_SIZE,
                    )
                )
        pairs.append(
            PairProfile(
                rows_variable=rows_var,
                rows_label=rg.label,
                columns_variable=cols_var,
                columns_label=cg.label,
                cells=cells,
            )
        )

    return RiskProfiles(
        cohort=cohort,
        n=n,
        at_risk=at,
        risk_percent=overall,
        risk_ci=_interval(at, n),
        threshold=RISK_THRESHOLD,
        single=single,
        pairs=pairs,
        notes=[*NOTES, *_data_notes(data)],
    )
