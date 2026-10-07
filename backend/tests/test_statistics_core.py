"""Exact checks of the numerical building blocks against hand-computed values and
known statistical identities."""

import math

import numpy as np
import pytest
from scipy import stats

from analytics.statistics import core


def test_holm_adjustment():
    assert core.holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_benjamini_hochberg_adjustment():
    assert core.benjamini_hochberg([0.01, 0.04, 0.03, 0.005]) == pytest.approx(
        [0.02, 0.04, 0.04, 0.02]
    )


def test_adjusted_p_values_are_never_smaller_and_capped_at_one():
    p = [0.2, 0.5, 0.9, 0.001]
    for adjusted in (core.holm(p), core.benjamini_hochberg(p)):
        assert all(a >= raw for a, raw in zip(adjusted, p, strict=True))
        assert all(0 <= a <= 1 for a in adjusted)


def test_mean_ci():
    low, high = core.mean_ci(np.array([1, 2, 3, 4, 5]))
    assert (low, high) == pytest.approx((1.0368, 4.9632), abs=1e-4)


def test_wilson_ci():
    assert core.wilson_ci(10, 20) == pytest.approx((0.2993, 0.7007), abs=1e-4)
    low, high = core.wilson_ci(0, 30)
    assert low == pytest.approx(0) and 0 < high < 0.15


def test_pearson_correlation_ci_uses_fisher_z():
    assert core.correlation_ci(0.5, 28, "pearson") == pytest.approx((0.156, 0.736), abs=1e-3)
    low, high = core.correlation_ci(0.5, 28, "spearman")
    assert low < 0.156 and high > 0.736  # Bonett–Wright SE is wider


def test_cohens_d_and_ci():
    assert core.cohens_d([1, 2, 3], [4, 5, 6]) == pytest.approx(-3.0)
    low, high = core.cohens_d_ci(0.5, 50, 50)
    assert low < 0.5 < high and high - low == pytest.approx(
        2 * 1.96 * math.sqrt(0.04 + 0.25 / 200), abs=1e-3
    )


def test_anova_effect_sizes():
    groups = [np.array([1, 2, 3]), np.array([4, 5, 6])]
    assert core.eta_squared(groups) == pytest.approx(13.5 / 17.5)
    assert core.omega_squared(groups) == pytest.approx(12.5 / 18.5)


def test_eta_squared_h():
    assert core.eta_squared_h(h=12.0, n=104, k=4) == pytest.approx(0.09)


def test_cramers_v():
    assert core.cramers_v(10, 100, 2, 2) == pytest.approx(math.sqrt(0.1))
    table = np.array([[10, 20], [30, 40]])
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    assert core.cramers_v(chi2, 100, 2, 2) == pytest.approx(
        abs(stats.contingency.association(table))
    )


def test_rank_biserial_bounds():
    assert core.rank_biserial(u_statistic=20, n1=4, n2=5) == pytest.approx(1)
    assert core.rank_biserial(u_statistic=0, n1=4, n2=5) == pytest.approx(-1)
    assert core.rank_biserial(u_statistic=10, n1=4, n2=5) == pytest.approx(0)


def test_welch_anova_with_two_groups_equals_welch_t_test():
    rng = np.random.default_rng(0)
    a, b = rng.normal(10, 2, 30), rng.normal(11, 4, 45)
    t = stats.ttest_ind(a, b, equal_var=False)
    f, _, _, p = core.welch_anova([a, b])
    assert f == pytest.approx(t.statistic**2)
    assert p == pytest.approx(t.pvalue)


def test_games_howell_with_two_groups_equals_welch_t_test():
    rng = np.random.default_rng(1)
    a, b = rng.normal(10, 2, 30), rng.normal(11, 4, 45)
    _, p = core.games_howell(a, b, k=2)
    assert p == pytest.approx(stats.ttest_ind(a, b, equal_var=False).pvalue, rel=1e-6)


def test_dunn_with_two_groups_equals_kruskal_wallis():
    rng = np.random.default_rng(2)
    a, b = rng.integers(0, 20, 30), rng.integers(3, 20, 25)
    ((_, _, z, p),) = core.dunn([a, b])
    h = stats.kruskal(a, b)
    assert z**2 == pytest.approx(h.statistic)
    assert p == pytest.approx(h.pvalue)


@pytest.mark.parametrize(
    ("fn", "value", "expected"),
    [
        (core.label_correlation, 0.05, "negligible"),
        (core.label_correlation, -0.35, "moderate"),
        (core.label_correlation, 0.5, "strong"),
        (core.label_d, 0.19, "negligible"),
        (core.label_d, -0.5, "medium"),
        (core.label_eta, 0.14, "large"),
    ],
)
def test_effect_size_labels(fn, value, expected):
    assert fn(value) == expected


def test_finite_makes_values_json_safe():
    assert core.finite(float("nan")) is None
    assert core.finite(float("inf")) is None
    assert core.finite(1) == 1.0
