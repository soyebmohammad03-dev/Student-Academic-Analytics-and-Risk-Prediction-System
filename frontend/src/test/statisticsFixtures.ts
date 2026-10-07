/**
 * Small, hand-written API responses for component tests. Shaped like the backend
 * models; values are arbitrary test data, not dataset results.
 */

const interval = (low: number, high: number) => ({ low, high, confidence: 0.95 });
const summary = (variable: string, label: string) => ({
  variable, label, scale: "grade", n: 40, mean: 10.5, mean_ci: interval(9.5, 11.5), median: 11,
  modes: [11], minimum: 0, maximum: 19, range: 19, variance: 16, std: 4, q1: 8, q3: 13, iqr: 5,
  skewness: -0.5, kurtosis: 0.2, note: null,
}); // prettier-ignore

const box = (key: string, label: string) => ({
  key, label, n: 20, whisker_low: 4, q1: 8, median: 11, q3: 13, whisker_high: 18, mean: 10.4,
  outliers: [{ value: 0, count: 1 }],
}); // prettier-ignore

const matrix = {
  method: "spearman",
  variables: ["G1", "G3"],
  labels: ["First period grade", "Final grade"],
  r: [[1, 0.8], [0.8, 1]],
  p_adjusted: [[0, 0.001], [0.001, 0]],
  n: 40,
}; // prettier-ignore

export function statisticsResponse(path: string, cohort: string): unknown {
  if (path.endsWith("/distributions"))
    return {
      cohort,
      grades: [
        {
          variable: "G3", label: "Final grade", summary: summary("G3", "Final grade"),
          counts: [{ value: 0, count: 2 }], zero_count: 2,
          shape: { skewness: -0.5, kurtosis: 0.2, shapiro_p: 0.01, description: "Left-skewed (test)." },
          summary_excluding_zeros: null,
        }, // prettier-ignore
      ],
      risk: {
        threshold: 10,
        n: 40,
        at_risk: 12,
        proportion: 0.3,
        proportion_ci: interval(0.18, 0.45),
        zero_grade_at_risk: 2,
      },
      observations: ["2 students (5.0%) have a final grade of 0."],
    };
  if (path.endsWith("/hypothesis-tests"))
    return {
      cohort,
      alpha: 0.05,
      correction: "Holm (test).",
      items: [
        {
          key: "RQ1", question: "Is weekly study time associated with final performance (G3)?",
          h0: "ρ = 0", h1: "ρ ≠ 0", analysis: "Spearman", evidence: "confirmatory",
          test: "Spearman correlation", statistic: 0.3, p: 0.01, p_adjusted: 0.04, significant: true,
          effect: { name: "Spearman ρ", value: 0.3, ci: interval(0.1, 0.5), magnitude: "moderate" },
          finding: "Weekly study time shows a statistically significant association with G3.",
          sensitivity: "Without zero grades: ρ = 0.31.",
        }, // prettier-ignore
      ],
    };
  if (path.endsWith("/correlations"))
    return {
      cohort,
      key_pairs: [correlation()],
      key_pairs_correction: "Holm",
      sensitivity_key_pairs: [correlation()],
      matrix,
    };
  if (path.endsWith("/associations"))
    return {
      cohort,
      correction: "BH",
      items: [
        {
          variable: "sex", label: "Sex", rows: [{ category: "F", label: "Female", at_risk: 5, n: 20, risk_percent: 25 }],
          test: "Pearson chi-square", statistic: 1.2, dof: 1, p: 0.27, p_adjusted: 0.4,
          cramers_v: 0.17, magnitude: "small", warnings: [],
        }, // prettier-ignore
      ],
    };
  if (path.endsWith("/descriptive"))
    return { cohort, n: 40, numeric: [summary("absences", "School absences")], categorical: [] };
  if (path.endsWith("/outliers"))
    return {
      cohort, method: "Tukey", excluded: {},
      items: [{ variable: "absences", label: "School absences", n: 40, lower_fence: -5, upper_fence: 15, below: 0, above: 3, count: 3, proportion: 0.075, z_count: 1 }],
    }; // prettier-ignore
  if (path.endsWith("/group-comparisons"))
    return {
      variable: "studytime", variable_label: "Weekly study time", outcome: "G3",
      groups: [
        { key: "1", label: "Less than 2 hours", n: 20, mean: 9, mean_ci: interval(8, 10), std: 3, median: 9, q1: 7, q3: 11, small: false, box: box("1", "Less than 2 hours") },
        { key: "2", label: "2 to 5 hours", n: 20, mean: 11, mean_ci: interval(10, 12), std: 3, median: 11, q1: 9, q3: 13, small: false, box: box("2", "2 to 5 hours") },
      ],
      normality: [{ group: "Less than 2 hours", n: 20, shapiro_p: 0.3, skewness: 0.1, adequate: true, basis: "ok" }],
      variance: { test: "Levene", statistic: 0.1, p: 0.7, equal_variances: true },
      test: "Welch's t-test", family: "parametric", statistic_name: "t", statistic: -2.1, df: "37.9",
      p: 0.04, significant: true,
      effect_sizes: [{ name: "Cohen's d", value: -0.66, ci: interval(-1.3, -0.02), magnitude: "medium" }],
      rationale: "Two groups (test).", posthoc_method: null, posthoc: [], warnings: [],
    }; // prettier-ignore
  if (path.endsWith("/charts"))
    return {
      cohort,
      histograms: [{ variable: "G3", label: "Final grade", n: 40, bins: [{ start: 9, end: 9, label: "9", count: 12 }, { start: 10, end: 10, label: "10", count: 28 }] }],
      bars: [{ variable: "sex", label: "Sex", n: 40, bars: [{ key: "F", label: "Female", count: 22, percent: 55 }, { key: "M", label: "Male", count: 18, percent: 45 }] }],
      boxplots: [{ variable: "studytime", variable_label: "Weekly study time", outcome: "G3", groups: [box("1", "Less than 2 hours")] }],
      scatters: [{ x: "G1", y: "G3", x_label: "First period grade", y_label: "Final grade", n: 40, points: [{ x: 10, y: 11, count: 3 }], spearman_r: 0.8 }],
      heatmap: matrix,
      risk_profile: [{ variable: "G1", label: "First period grade", statistic: "mean", at_risk: 7.5, not_at_risk: 12.4, standardised_difference: -1.9 }],
      crosstab: {
        rows_variable: "studytime", columns_variable: "has_past_failures", outcome: "G3",
        row_labels: ["Less than 2 hours"], column_labels: ["No past failures", "1 or more"],
        cells: [{ row: "Less than 2 hours", column: "No past failures", n: 15, mean: 11.2 }, { row: "Less than 2 hours", column: "1 or more", n: 0, mean: null }],
      },
    }; // prettier-ignore
  throw new Error(`No fixture for ${path}`);
}

function correlation() {
  return {
    x: "studytime", y: "G3", x_label: "Weekly study time", y_label: "Final grade",
    method: "spearman", method_reason: "ordinal", r: 0.3, r_ci: interval(0.1, 0.5), p: 0.01,
    p_adjusted: 0.04, n: 40, strength: "moderate", interpretation: "…", pearson_r: 0.28, spearman_r: 0.3,
  }; // prettier-ignore
}
