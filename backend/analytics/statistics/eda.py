"""Chart-ready exploratory data. Every number is computed from the cohort data; the
frontend only draws it."""

from __future__ import annotations

import pandas as pd

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.preprocessing import RISK_LABEL
from analytics.statistics.core import cohens_d, finite
from analytics.statistics.correlation import spearman_matrix
from analytics.statistics.descriptive import box_summary, categorical_summary
from analytics.statistics.groups import GROUPINGS
from analytics.statistics.models import (
    Bar,
    BarChart,
    BoxPlot,
    CrossTab,
    CrossTabCell,
    Eda,
    Histogram,
    HistogramBin,
    ProfileRow,
    Scatter,
    ScatterPoint,
)

BAR_VARIABLES = (
    "studytime",
    "failures",
    "sex",
    "school",
    "address",
    "schoolsup",
    "famsup",
    "paid",
    "internet",
    "higher",
    "Medu",
    "Fedu",
)
BOX_VARIABLES = (
    "studytime",
    "failures",
    "absence_band",
    "Medu",
    "Fedu",
    "schoolsup",
    "famsup",
    "sex",
)
SCATTER_PAIRS = (("G1", "G3"), ("G2", "G3"), ("absences", "G3"))
PROFILE_NUMERIC = (
    "G1",
    "G2",
    "studytime",
    "failures",
    "absences",
    "age",
    "Medu",
    "Fedu",
    "goout",
    "Dalc",
    "Walc",
    "health",
    "freetime",
)
PROFILE_BINARY = ("schoolsup", "famsup", "paid", "higher", "internet", "romantic")


def histogram(values: pd.Series, name: str, width: int = 1) -> Histogram:
    """Integer bins of ``width``. Width 1 covers the documented range (e.g. grades 0–20)."""
    x = values.astype(int)
    top = int(COLUMNS_BY_NAME[name].maximum) if width == 1 else int(x.max())
    bins = []
    for start in range(0, top + 1, width):
        end = start + width - 1
        bins.append(
            HistogramBin(
                start=start,
                end=end,
                label=str(start) if width == 1 else f"{start}–{end}",
                count=int(((x >= start) & (x <= end)).sum()),
            )
        )
    return Histogram(variable=name, label=COLUMNS_BY_NAME[name].label, n=len(x), bins=bins)


def bar_chart(data: pd.DataFrame, name: str) -> BarChart:
    if name in GROUPINGS and not COLUMNS_BY_NAME[name].allowed:
        grouping = GROUPINGS[name]
        keys = grouping.assign(data)
        n = len(keys)
        bars = [
            Bar(key=k, label=lbl, count=int((keys == k).sum()), percent=100 * (keys == k).mean())
            for k, lbl in grouping.levels
        ]
        return BarChart(variable=name, label=grouping.label, n=n, bars=bars)
    summary = categorical_summary(
        data[name].astype("int64").astype(str)
        if pd.api.types.is_numeric_dtype(data[name])
        else data[name],
        name,
    )
    return BarChart(
        variable=name,
        label=summary.label,
        n=summary.n,
        bars=[
            Bar(key=c.value, label=c.label, count=c.count, percent=c.percent)
            for c in summary.categories
        ],
    )


def box_plot(data: pd.DataFrame, variable: str, outcome: str = "G3") -> BoxPlot:
    grouping = GROUPINGS[variable]
    keys = grouping.assign(data)
    y = data[outcome].astype(float)
    groups = [
        box_summary(k, lbl, y[keys == k].to_numpy())
        for k, lbl in grouping.levels
        if (keys == k).any()
    ]
    return BoxPlot(variable=variable, variable_label=grouping.label, outcome=outcome, groups=groups)


def scatter(data: pd.DataFrame, x: str, y: str) -> Scatter:
    pairs = data[[x, y]].astype(int).value_counts().sort_index()
    from scipy import stats

    return Scatter(
        x=x,
        y=y,
        x_label=COLUMNS_BY_NAME[x].label,
        y_label=COLUMNS_BY_NAME[y].label,
        n=len(data),
        points=[ScatterPoint(x=float(a), y=float(b), count=int(c)) for (a, b), c in pairs.items()],
        spearman_r=finite(stats.spearmanr(data[x], data[y]).statistic),
    )


def risk_profile(data: pd.DataFrame) -> list[ProfileRow]:
    risk = data[RISK_LABEL] == 1
    rows = []
    for name in PROFILE_NUMERIC:
        a, b = data.loc[risk, name].astype(float), data.loc[~risk, name].astype(float)
        rows.append(
            ProfileRow(
                variable=name,
                label=COLUMNS_BY_NAME[name].label,
                statistic="mean",
                at_risk=finite(a.mean()),
                not_at_risk=finite(b.mean()),
                standardised_difference=finite(cohens_d(a, b)),
            )
        )
    for name in PROFILE_BINARY:
        yes = data[name] == "yes"
        rows.append(
            ProfileRow(
                variable=name,
                label=COLUMNS_BY_NAME[name].label,
                statistic="percent",
                at_risk=finite(100 * yes[risk].mean()),
                not_at_risk=finite(100 * yes[~risk].mean()),
                standardised_difference=None,
            )
        )
    return rows


def crosstab(data: pd.DataFrame) -> CrossTab:
    rows_g, cols_g = GROUPINGS["studytime"], GROUPINGS["has_past_failures"]
    r_keys, c_keys = rows_g.assign(data), cols_g.assign(data)
    cells = []
    for rk, rl in rows_g.levels:
        for ck, cl in cols_g.levels:
            sel = data.loc[(r_keys == rk) & (c_keys == ck), "G3"].astype(float)
            cells.append(
                CrossTabCell(
                    row=rl, column=cl, n=len(sel), mean=finite(sel.mean()) if len(sel) else None
                )
            )
    return CrossTab(
        rows_variable="studytime",
        columns_variable="has_past_failures",
        outcome="G3",
        row_labels=[lbl for _, lbl in rows_g.levels],
        column_labels=[lbl for _, lbl in cols_g.levels],
        cells=cells,
    )


def eda(data: pd.DataFrame, cohort: str) -> Eda:
    return Eda(
        cohort=cohort,
        histograms=[histogram(data[g], g) for g in ("G1", "G2", "G3")]
        + [histogram(data["absences"], "absences", width=5)],
        bars=[bar_chart(data, v) for v in BAR_VARIABLES],
        boxplots=[box_plot(data, v) for v in BOX_VARIABLES],
        scatters=[scatter(data, x, y) for x, y in SCATTER_PAIRS],
        heatmap=spearman_matrix(data),
        risk_profile=risk_profile(data),
        crosstab=crosstab(data),
    )
