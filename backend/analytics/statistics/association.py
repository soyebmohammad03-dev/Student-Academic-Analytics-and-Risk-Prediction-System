"""Association between categorical variables and academic risk (chi-square).

Pearson's chi-square test of independence is used without Yates' continuity correction.
When a 2×2 table has an expected count below 5, Fisher's exact test is used instead.
For larger tables with expected counts below 5, the result is flagged rather than
silently trusted. Effect size: Cramér's V.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from analytics.preprocessing import RISK_LABEL
from analytics.statistics.core import (
    benjamini_hochberg,
    cramers_v,
    finite,
    label_cramers_v,
    wilson_ci,
)
from analytics.statistics.groups import ASSOCIATION_VARIABLES, GROUPINGS, Grouping
from analytics.statistics.models import Association, Associations, ContingencyRow, Interval


def associate(data: pd.DataFrame, grouping: Grouping | str) -> Association:
    grouping = GROUPINGS[grouping] if isinstance(grouping, str) else grouping
    keys = grouping.assign(data)
    risk = data[RISK_LABEL].astype(int)
    rows, table = [], []
    for key, label in grouping.levels:
        mask = keys == key
        n = int(mask.sum())
        if n == 0:
            continue
        at = int(risk[mask].sum())
        low, high = wilson_ci(at, n)
        rows.append(
            ContingencyRow(
                category=key,
                label=label,
                at_risk=at,
                not_at_risk=n - at,
                n=n,
                risk_percent=100 * at / n,
                risk_ci=Interval(low=finite(low), high=finite(high)),
            )
        )
        table.append([at, n - at])
    observed = np.array(table)
    chi2, p, dof, expected = stats.chi2_contingency(observed, correction=False)
    min_expected = float(expected.min())
    warnings: list[str] = []
    test, statistic, dof_out = "Pearson chi-square", chi2, int(dof)
    if observed.shape == (2, 2) and min_expected < 5:
        test, dof_out = "Fisher's exact test", None
        statistic, p = stats.fisher_exact(observed)
        warnings.append("Expected count below 5 in a 2×2 table: Fisher's exact test used.")
    elif (expected < 5).mean() > 0.2:
        warnings.append(
            "More than 20% of expected counts are below 5; the chi-square approximation "
            "may be unreliable."
        )
    if grouping.note:
        warnings.append(grouping.note)
    v = cramers_v(chi2, int(observed.sum()), *observed.shape)
    return Association(
        variable=grouping.variable,
        label=grouping.label,
        rows=rows,
        test=test,
        statistic=finite(statistic),
        dof=dof_out,
        p=finite(p),
        cramers_v=finite(v),
        magnitude=label_cramers_v(v, *observed.shape),
        min_expected=finite(min_expected),
        warnings=warnings,
    )


def associations(data: pd.DataFrame, cohort: str) -> Associations:
    items = [associate(data, v) for v in ASSOCIATION_VARIABLES]
    for item, adjusted in zip(items, benjamini_hochberg([i.p for i in items]), strict=True):
        item.p_adjusted = finite(adjusted)
    return Associations(
        cohort=cohort,
        correction=(
            "Benjamini–Hochberg (false discovery rate) across all association tests; exploratory."
        ),
        items=items,
    )
