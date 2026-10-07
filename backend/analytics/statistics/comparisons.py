"""Group comparisons of a numeric outcome (G3 by default) with automatic test selection.

Selection rule (fixed in advance, applied identically to every comparison):

1. **Normality, per group.** A group is adequate for a mean-based test if Shapiro–Wilk
   does not reject normality, or if n ≥ 30 and |skewness| ≤ 1 (the sampling
   distribution of the mean is then approximately normal by the central limit theorem).
2. **Variance homogeneity.** Levene's test (median-centred, Brown–Forsythe).
3. **Choice.**
   - Two groups, all adequate: Welch's t-test (no equal-variance assumption);
     effect size Cohen's d.
   - Two groups, otherwise: Mann–Whitney U; effect size rank-biserial r.
   - 3+ groups, all adequate, equal variances: one-way ANOVA + Tukey HSD;
     η² and ω².
   - 3+ groups, all adequate, unequal variances: Welch's ANOVA + Games–Howell.
   - 3+ groups, otherwise: Kruskal–Wallis + Dunn's test (Holm-adjusted); η²_H.
4. **Post-hoc tests** run only when the omnibus test is significant (p < α).

**Independence.** Each row is a different student within one cohort, so groups are
independent by design. Students who appear in both cohorts are never pooled, because
each cohort is analysed separately.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from analytics.statistics.config import ALPHA, LARGE_SAMPLE, MAX_ABS_SKEW, MIN_GROUP_SIZE
from analytics.statistics.core import (
    cohens_d,
    cohens_d_ci,
    dunn,
    eta_squared,
    eta_squared_h,
    finite,
    games_howell,
    holm,
    label_correlation,
    label_d,
    label_eta,
    mean_ci,
    omega_squared,
    rank_biserial,
    welch_anova,
    welch_mean_difference_ci,
)
from analytics.statistics.descriptive import box_summary
from analytics.statistics.groups import GROUPINGS, Grouping
from analytics.statistics.models import (
    EffectSize,
    GroupComparison,
    GroupSummary,
    Interval,
    NormalityCheck,
    PostHocComparison,
    VarianceCheck,
)


def check_normality(label: str, x: np.ndarray) -> NormalityCheck:
    n = len(x)
    skew = float(stats.skew(x, bias=False)) if n > 2 else float("nan")
    if n < 3 or np.ptp(x) == 0:
        return NormalityCheck(
            group=label,
            n=n,
            shapiro_w=None,
            shapiro_p=None,
            skewness=finite(skew),
            adequate=False,
            basis="Too few or identical values to assess normality.",
        )
    w, p = stats.shapiro(x)
    if p >= ALPHA:
        adequate, basis = True, f"Shapiro–Wilk does not reject normality (p = {p:.3g})."
    elif n >= LARGE_SAMPLE and abs(skew) <= MAX_ABS_SKEW:
        adequate, basis = (
            True,
            (
                f"Normality rejected, but n = {n} ≥ {LARGE_SAMPLE} with |skew| = {abs(skew):.2f} "
                f"≤ {MAX_ABS_SKEW}: mean-based tests are robust here."
            ),
        )
    else:
        adequate, basis = (
            False,
            (
                f"Normality rejected (p = {p:.3g}) and the group is too small or too skewed "
                "for mean-based tests."
            ),
        )
    return NormalityCheck(
        group=label,
        n=n,
        shapiro_w=finite(w),
        shapiro_p=finite(p),
        skewness=finite(skew),
        adequate=adequate,
        basis=basis,
    )


def _summary(key: str, label: str, x: np.ndarray) -> GroupSummary:
    low, high = mean_ci(x) if len(x) > 1 else (None, None)
    q1, med, q3 = np.percentile(x, [25, 50, 75]) if len(x) else (np.nan,) * 3
    return GroupSummary(
        key=key,
        label=label,
        n=len(x),
        mean=finite(x.mean()) if len(x) else None,
        mean_ci=Interval(low=finite(low), high=finite(high)),
        std=finite(x.std(ddof=1)) if len(x) > 1 else None,
        median=finite(med),
        q1=finite(q1),
        q3=finite(q3),
        small=len(x) < MIN_GROUP_SIZE,
        box=box_summary(key, label, x),
    )


def compare_groups(
    data: pd.DataFrame,
    grouping: Grouping | str,
    outcome: str = "G3",
) -> GroupComparison:
    grouping = GROUPINGS[grouping] if isinstance(grouping, str) else grouping
    keys = grouping.assign(data)
    y = data[outcome].astype(float)
    present = [(k, lbl) for k, lbl in grouping.levels if (keys == k).any()]
    samples = [y[keys == k].to_numpy() for k, _ in present]
    labels = [lbl for _, lbl in present]
    if len(samples) < 2:
        raise ValueError(f"{grouping.variable} has fewer than two non-empty groups.")

    warnings = [
        f"Group '{lbl}' has only {len(s)} students; its estimates are imprecise."
        for lbl, s in zip(labels, samples, strict=True)
        if len(s) < MIN_GROUP_SIZE
    ]
    if grouping.note:
        warnings.append(grouping.note)

    normality = [check_normality(lbl, s) for lbl, s in zip(labels, samples, strict=True)]
    lev = stats.levene(*samples, center="median")
    variance = VarianceCheck(
        statistic=finite(lev.statistic),
        p=finite(lev.pvalue),
        equal_variances=bool(lev.pvalue >= ALPHA),
    )
    parametric = all(c.adequate for c in normality)
    k = len(samples)
    effects: list[EffectSize] = []
    posthoc: list[PostHocComparison] = []
    posthoc_method: str | None = None

    if k == 2:
        a, b = samples
        if parametric:
            res = stats.ttest_ind(a, b, equal_var=False)
            test, stat_name, stat, p = "Welch's t-test", "t", res.statistic, res.pvalue
            df = f"{res.df:.1f}"
            d = cohens_d(a, b)
            lo, hi = cohens_d_ci(d, len(a), len(b))
            dlo, dhi = welch_mean_difference_ci(a, b)
            effects = [
                EffectSize(
                    name=f"Cohen's d ({labels[0]} − {labels[1]})",
                    value=finite(d),
                    ci=Interval(low=finite(lo), high=finite(hi)),
                    magnitude=label_d(d),
                ),
                EffectSize(
                    name=f"Mean difference ({labels[0]} − {labels[1]}), grade points",
                    value=finite(a.mean() - b.mean()),
                    ci=Interval(low=finite(dlo), high=finite(dhi)),
                    magnitude=label_d(d),
                ),
            ]
            rationale = (
                "Two independent groups; both adequate for a mean-based test. Welch's t-test "
                "does not assume equal variances."
            )
        else:
            res = stats.mannwhitneyu(a, b, alternative="two-sided")
            test, stat_name, stat, p, df = "Mann–Whitney U", "U", res.statistic, res.pvalue, None
            r = rank_biserial(res.statistic, len(a), len(b))
            effects = [
                EffectSize(
                    name=f"Rank-biserial r ({labels[0]} vs {labels[1]})",
                    value=finite(r),
                    magnitude=label_correlation(r),
                )
            ]
            rationale = (
                "Two independent groups; at least one is not adequate for a mean-based test, so "
                "the rank-based Mann–Whitney U test is used."
            )
    else:
        if parametric and variance.equal_variances:
            res = stats.f_oneway(*samples)
            n_total = sum(len(s) for s in samples)
            test, stat_name, stat, p = "One-way ANOVA", "F", res.statistic, res.pvalue
            df = f"{k - 1}, {n_total - k}"
            rationale = (
                "Three or more groups, all adequate for mean-based tests, with equal variances "
                "(Levene)."
            )
            if p < ALPHA:
                posthoc_method = "Tukey HSD (family-wise error controlled)"
                tukey = stats.tukey_hsd(*samples)
                posthoc = [
                    PostHocComparison(
                        group_a=labels[i],
                        group_b=labels[j],
                        estimate=finite(samples[i].mean() - samples[j].mean()),
                        p_adjusted=finite(tukey.pvalue[i][j]),
                        significant=bool(tukey.pvalue[i][j] < ALPHA),
                    )
                    for i in range(k)
                    for j in range(i + 1, k)
                ]
        elif parametric:
            f, df1, df2, p = welch_anova(samples)
            test, stat_name, stat, df = "Welch's ANOVA", "F", f, f"{df1:.0f}, {df2:.1f}"
            rationale = (
                "Three or more groups, adequate for mean-based tests, but variances differ "
                "(Levene), so Welch's ANOVA is used."
            )
            if p < ALPHA:
                posthoc_method = "Games–Howell (unequal variances)"
                for i in range(k):
                    for j in range(i + 1, k):
                        diff, pij = games_howell(samples[i], samples[j], k)
                        posthoc.append(
                            PostHocComparison(
                                group_a=labels[i],
                                group_b=labels[j],
                                estimate=finite(diff),
                                p_adjusted=finite(pij),
                                significant=bool(pij < ALPHA),
                            )
                        )
        else:
            res = stats.kruskal(*samples)
            n_total = sum(len(s) for s in samples)
            test, stat_name, stat, p, df = (
                "Kruskal–Wallis H",
                "H",
                res.statistic,
                res.pvalue,
                f"{k - 1}",
            )
            rationale = (
                "Three or more groups; at least one is not adequate for a mean-based test, so "
                "the rank-based Kruskal–Wallis test is used."
            )
            effects = [
                EffectSize(
                    name="η²_H (rank-based)",
                    value=finite(eta_squared_h(res.statistic, n_total, k)),
                    magnitude=label_eta(eta_squared_h(res.statistic, n_total, k)),
                )
            ]
            if p < ALPHA:
                posthoc_method = "Dunn's test, Holm-adjusted"
                pairs = dunn(samples)
                adjusted = holm([pp for *_, pp in pairs])
                posthoc = [
                    PostHocComparison(
                        group_a=labels[i],
                        group_b=labels[j],
                        estimate=finite(z),
                        p_adjusted=finite(pa),
                        significant=bool(pa < ALPHA),
                    )
                    for (i, j, z, _), pa in zip(pairs, adjusted, strict=True)
                ]
        if not effects:
            eta = eta_squared(samples)
            omega = omega_squared(samples)
            effects = [
                EffectSize(name="η²", value=finite(eta), magnitude=label_eta(eta)),
                EffectSize(name="ω²", value=finite(omega), magnitude=label_eta(omega)),
            ]

    return GroupComparison(
        variable=grouping.variable,
        variable_label=grouping.label,
        outcome=outcome,
        groups=[_summary(k_, lbl, s) for (k_, lbl), s in zip(present, samples, strict=True)],
        normality=normality,
        variance=variance,
        test=test,
        family="parametric"
        if test in {"Welch's t-test", "One-way ANOVA", "Welch's ANOVA"}
        else "non-parametric",
        statistic_name=stat_name,
        statistic=finite(stat),
        df=df,
        p=finite(p),
        significant=bool(p < ALPHA),
        effect_sizes=effects,
        rationale=rationale,
        posthoc_method=posthoc_method,
        posthoc=posthoc,
        warnings=warnings,
    )
