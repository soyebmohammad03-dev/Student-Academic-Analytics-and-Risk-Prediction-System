import numpy as np
import pandas as pd
import pytest

from analytics.statistics import (
    associate,
    compare_groups,
    correlate,
    describe,
    distributions,
    eda,
    outliers,
    research_questions,
)
from analytics.statistics.correlation import choose_method
from analytics.statistics.descriptive import numeric_summary
from analytics.statistics.outliers import screen

# --- Descriptive ---------------------------------------------------------------------


def test_numeric_summary_matches_hand_computation():
    s = numeric_summary(pd.Series([1, 2, 2, 3, 10]), "absences")

    assert (s.n, s.mean, s.median, s.modes) == (5, 3.6, 2, [2.0])
    assert s.variance == pytest.approx(13.3)
    assert s.std == pytest.approx(13.3**0.5)
    assert (s.minimum, s.maximum, s.range) == (1, 10, 9)
    assert (s.q1, s.q3, s.iqr) == (2, 3, 1)


def test_modes_include_ties():
    assert numeric_summary(pd.Series([1, 1, 2, 2, 3]), "health").modes == [1.0, 2.0]


def test_nominal_variables_get_frequencies_not_means(analytical):
    result = describe(analytical, "math")
    numeric = {s.variable for s in result.numeric}
    categorical = {c.variable: c for c in result.categorical}

    assert "Mjob" not in numeric and "Mjob" in categorical
    assert sum(c.percent for c in categorical["Mjob"].categories) == pytest.approx(100)
    assert sum(c.count for c in categorical["Mjob"].categories) == len(analytical)
    assert {"G3", "absences", "studytime", "failures", "age", "health", "goout"} <= numeric


def test_ordinal_summaries_are_flagged():
    s = numeric_summary(pd.Series([1, 2, 3, 4]), "studytime")
    assert s.note and "ordinal" in s.note.lower()


# --- Distributions -----------------------------------------------------------------------


def test_zero_grades_are_counted_and_kept(analytical):
    analytical["G3"] = analytical["G3"].clip(lower=1)
    analytical.loc[analytical.index[:5], "G3"] = 0
    analytical["at_risk"] = (analytical["G3"] < 10).astype(int)
    result = distributions(analytical, "math")
    g3 = next(g for g in result.grades if g.variable == "G3")

    assert g3.zero_count == 5
    assert g3.summary.n == len(analytical)
    assert g3.summary_excluding_zeros.n == len(analytical) - 5
    assert sum(c.count for c in g3.counts) == len(analytical)
    assert result.risk.zero_grade_at_risk == 5
    assert any("final grade of 0" in o for o in result.observations)


# --- Correlation ------------------------------------------------------------------------


def test_method_choice_follows_variable_type():
    x = pd.Series(np.random.default_rng(0).normal(size=50))
    assert choose_method(x, x, "studytime", "G3")[0] == "spearman"
    assert choose_method(x, x, "absences", "G3")[0] == "spearman"
    assert choose_method(x, x, "x_normal", "y_normal")[0] == "pearson"


def test_correlation_reports_coefficient_p_n_and_ci():
    rng = np.random.default_rng(3)
    data = pd.DataFrame({"studytime": rng.integers(1, 5, 200)})
    data["G3"] = (data["studytime"] * 2 + rng.normal(0, 2, 200)).round().clip(0, 20)
    result = correlate(data, "studytime", "G3")

    assert result.method == "spearman" and result.n == 200
    assert 0 < result.r < 1 and result.r_ci.low < result.r < result.r_ci.high
    assert 0 <= result.p < 0.05
    assert "not evidence of cause" in result.interpretation


# --- Group comparisons -------------------------------------------------------------------


def _frame(groups: dict[str, np.ndarray], variable: str) -> pd.DataFrame:
    return pd.DataFrame(
        {variable: np.concatenate([[k] * len(v) for k, v in groups.items()]),
         "G3": np.concatenate(list(groups.values()))}
    )  # fmt: skip


RNG = np.random.default_rng(42)


def test_two_normal_groups_use_welch_t_test():
    data = _frame({"F": RNG.normal(11, 3, 60), "M": RNG.normal(10, 3, 60)}, "sex")
    result = compare_groups(data, "sex")

    assert result.test == "Welch's t-test" and result.family == "parametric"
    assert result.effect_sizes[0].name.startswith("Cohen's d")
    assert (
        result.effect_sizes[0].ci.low
        < result.effect_sizes[0].value
        < result.effect_sizes[0].ci.high
    )


def test_small_skewed_groups_use_mann_whitney():
    data = _frame({"F": RNG.exponential(2, 12), "M": RNG.exponential(4, 12) ** 2}, "sex")
    result = compare_groups(data, "sex")

    assert result.test == "Mann–Whitney U" and result.family == "non-parametric"
    assert result.effect_sizes[0].name.startswith("Rank-biserial")
    assert any(not c.adequate for c in result.normality)


def test_normal_equal_variance_groups_use_anova_with_tukey():
    data = _frame({str(k): RNG.normal(8 + k, 2, 50) for k in (1, 2, 3, 4)}, "studytime")
    result = compare_groups(data, "studytime")

    assert result.test == "One-way ANOVA" and result.variance.equal_variances
    assert result.significant and result.posthoc_method.startswith("Tukey")
    assert len(result.posthoc) == 6
    assert {e.name for e in result.effect_sizes} == {"η²", "ω²"}


def test_unequal_variances_use_welch_anova_with_games_howell():
    data = _frame({str(k): RNG.normal(8 + k, k**1.5, 60) for k in (1, 2, 3, 4)}, "studytime")
    result = compare_groups(data, "studytime")

    assert not result.variance.equal_variances
    assert result.test == "Welch's ANOVA"
    assert result.posthoc_method.startswith("Games–Howell")


def test_non_normal_groups_use_kruskal_wallis_with_dunn():
    data = _frame({str(k): RNG.exponential(k, 15) ** 2 for k in (1, 2, 3, 4)}, "studytime")
    result = compare_groups(data, "studytime")

    assert result.test == "Kruskal–Wallis H"
    if result.significant:
        assert result.posthoc_method.startswith("Dunn")
        assert all(0 <= c.p_adjusted <= 1 for c in result.posthoc)


def test_posthoc_only_runs_when_omnibus_is_significant():
    same = np.random.default_rng(5).normal(10, 2, 40)
    data = _frame({str(k): same for k in (1, 2, 3)}, "studytime")  # identical groups
    result = compare_groups(data, "studytime")

    assert not result.significant
    assert result.posthoc == [] and result.posthoc_method is None


def test_small_groups_are_warned_about():
    data = _frame({"1": RNG.normal(10, 2, 5), "2": RNG.normal(10, 2, 40)}, "studytime")
    assert any("only 5 students" in w for w in compare_groups(data, "studytime").warnings)


# --- Association ------------------------------------------------------------------------


def test_chi_square_contingency_and_cramers_v():
    data = pd.DataFrame(
        {"sex": ["F"] * 50 + ["M"] * 50, "at_risk": [1] * 10 + [0] * 40 + [1] * 25 + [0] * 25}
    )
    result = associate(data, "sex")

    assert result.test == "Pearson chi-square" and result.dof == 1
    assert [(r.at_risk, r.not_at_risk) for r in result.rows] == [(10, 40), (25, 25)]
    assert result.rows[0].risk_percent == 20
    assert result.statistic == pytest.approx(9.890, abs=1e-3)
    assert result.cramers_v == pytest.approx((9.890 / 100) ** 0.5, abs=1e-3)


def test_fisher_exact_is_used_for_sparse_2x2_tables():
    data = pd.DataFrame(
        {"sex": ["F"] * 6 + ["M"] * 30, "at_risk": [1] * 5 + [0] + [1] * 2 + [0] * 28}
    )
    result = associate(data, "sex")

    assert result.test == "Fisher's exact test"
    assert result.warnings


# --- Outliers ----------------------------------------------------------------------------


def test_iqr_screen_flags_without_removing():
    values = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 50])
    report = screen(values, "absences")

    assert (report.q1, report.q3) == (3.25, 7.75)
    assert report.upper_fence == pytest.approx(14.5)
    assert (report.above, report.below, report.count) == (1, 0, 1)
    assert report.proportion == pytest.approx(0.1)
    assert report.n == len(values)
    assert [(v.value, v.count) for v in report.flagged_values] == [(50, 1)]


# --- End to end on synthetic cohorts ------------------------------------------------------


@pytest.mark.parametrize("cohort", ["math", "portuguese"])
def test_all_analyses_produce_valid_json_safe_results(analytical, cohort):
    analyses = (describe, distributions, outliers, eda, research_questions)
    outputs = [analysis(analytical, cohort) for analysis in analyses]
    for output in outputs:
        text = output.model_dump_json()
        assert "NaN" not in text and "Infinity" not in text


def test_research_questions_structure(analytical):
    rq = research_questions(analytical, "math")

    assert [q.key for q in rq.items] == [
        "RQ1",
        "RQ2",
        "RQ3",
        "RQ4",
        "RQ5",
        "RQ6a",
        "RQ6b",
        "RQ7",
        "RQ8",
    ]
    confirmatory = [q for q in rq.items if q.evidence == "confirmatory"]
    assert len(confirmatory) == 7
    for q in confirmatory:
        assert 0 <= q.p <= q.p_adjusted <= 1
        assert q.significant == (q.p_adjusted < 0.05)
