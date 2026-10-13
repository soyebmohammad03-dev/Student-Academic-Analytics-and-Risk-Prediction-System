import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expectNoAxeViolations } from "@/test/axe";
import { afterEach, describe, expect, it, vi } from "vitest";

import { json, mockFetch } from "@/test/api";

import { ModelComparisonView } from "./ModelComparisonView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const summary = (mean: number) => ({
  mean,
  std: 0.05,
  folds: [mean, mean, mean, mean, mean],
  defined_folds: 5,
});

function result(url: URL, model: string, label: string, baseline: boolean, f1: number) {
  const task = url.searchParams.get("task");
  const metrics =
    task === "regression"
      ? { mae: 3 - f1, rmse: 4 - f1, r2: f1 / 2 }
      : { precision: f1, recall: f1, f1, roc_auc: 0.5 + f1 / 2 };
  return {
    cohort: url.searchParams.get("cohort"),
    task,
    scenario: url.searchParams.get("scenario"),
    model,
    label,
    family: "fixture",
    baseline,
    complexity: 1,
    class_weight: null,
    search_space: {},
    candidates: 1,
    best_params: {},
    outer_fold_params: [],
    cv: Object.fromEntries(Object.entries(metrics).map(([k, v]) => [k, summary(v)])),
    test: metrics,
    test_confusion: null,
    test_predicted_positive: null,
    n_train: 32,
    n_test: 8,
    diagnostics: [],
  };
}

function selected(url: URL) {
  const task = url.searchParams.get("task");
  const scenario = url.searchParams.get("scenario");
  const cohort = url.searchParams.get("cohort");
  return {
    metadata: {
      cohort,
      task,
      scenario,
      model: "tree",
      label: "Fixture tree",
      feature_columns: ["a", "b"],
      target: task === "regression" ? "G3" : "at_risk",
      positive_class: null,
      threshold: 0.5,
      score_kind: "probability",
      best_params: { max_depth: 3 },
      cv_folds: 5,
      cv_strategy: "fixture",
      n_train: 32,
      n_test: 8,
      created_at: "2026-01-01T00:00:00+00:00",
    },
    selection: {
      cohort,
      task,
      scenario,
      model: "tree",
      label: "Fixture tree",
      primary_metric: task === "regression" ? "rmse" : "f1",
      best_model: "tree",
      best_mean: 0.6,
      tolerance: 0.02,
      within_tolerance: ["tree"],
      beats_baseline: true,
      baseline_mean: 0,
      reason: "Fixture selection reason.",
    },
    regression_errors:
      task === "regression"
        ? {
            cohort,
            scenario,
            model: "tree",
            n: 8,
            metrics: {},
            residuals: {
              mean: 0.1,
              std: 1,
              median: 0,
              q1: -1,
              q3: 1,
              min: -3,
              max: 2,
              within_1: 0.5,
              within_2: 0.75,
            },
            histogram: [
              { start: -1, end: 0, label: "-1 to 0", count: 4 },
              { start: 0, end: 1, label: "0 to 1", count: 4 },
            ],
            by_band: [{ band: "G3 ≥ 10", n: 8, mae: 1, mean_residual: 0.1 }],
            largest: [],
            patterns: ["Fixture regression pattern."],
          }
        : null,
    classification_errors:
      task === "classification"
        ? {
            cohort,
            scenario,
            model: "tree",
            n: 8,
            threshold: 0.5,
            score_kind: "probability",
            confusion: { tn: 4, fp: 1, fn: 2, tp: 1 },
            metrics: {},
            by_class: [],
            false_negative_grades: [{ grade: 9, count: 2 }],
            false_positive_grades: [],
            zero_grade_detected: 0,
            zero_grade_total: 0,
            patterns: ["Fixture classification pattern."],
          }
        : null,
    zero_grade_sensitivity: null,
  };
}

function routes() {
  return mockFetch({
    "/models/evaluations": (url) =>
      json([
        result(url, "majority", "Fixture baseline", true, 0),
        result(url, "tree", "Fixture tree", false, 0.6),
        result(url, "forest", "Fixture forest", false, 0.55),
      ]),
    "/models/selected": (url) => json(selected(url)),
    "/models/scenario-comparison": (url) =>
      json({
        cohort: url.searchParams.get("cohort"),
        task: url.searchParams.get("task"),
        primary_metric: url.searchParams.get("task") === "regression" ? "rmse" : "f1",
        rows: [],
        note: "Fixture scenario note.",
      }),
    "/models/cohort-comparison": () => json({ cohorts: [], differences: ["Fixture difference."] }),
  });
}

describe("ModelComparisonView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists every model with CV and held-out test metrics labelled separately", async () => {
    routes();
    render(<ModelComparisonView />);

    const table = await screen.findByRole("table", { name: /every candidate model/i });
    expect(within(table).getByText(/Cross-validation · training set/)).toBeInTheDocument();
    expect(within(table).getByText(/Held-out test set \(n = 8\), scored once/)).toBeInTheDocument();
    const rows = within(table).getAllByRole("row").slice(2);
    // Sorted by CV F1; the baseline comes last.
    expect(rows.map((r) => within(r).getByRole("rowheader").textContent)).toEqual([
      expect.stringContaining("Fixture tree"),
      expect.stringContaining("Fixture forest"),
      expect.stringContaining("Fixture baseline"),
    ]);
    expect(within(rows[0]).getByText("Selected")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Baseline")).toBeInTheDocument();
  });

  it("explains the selection and makes weak recall visible", async () => {
    routes();
    render(<ModelComparisonView />);
    expect(await screen.findByText("Fixture selection reason.")).toBeInTheDocument();
    expect(screen.getByText("Limited recall")).toBeInTheDocument();
    expect(screen.getByText(/flagged 1 of the 3 students/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /Held-out test set, n = 8/ })).toBeInTheDocument();
  });

  it("switches to regression metrics and refetches", async () => {
    const fetchMock = routes();
    render(<ModelComparisonView />);
    await screen.findByText("Fixture selection reason.");

    fireEvent.click(screen.getByRole("radio", { name: "Final grade" }));
    expect(await screen.findByText("Fixture regression pattern.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "What is Root mean squared error?" }).length).toBe(
      2,
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls
          .map(([u]) => new URL(u))
          .some(
            (u) =>
              u.pathname.endsWith("/evaluations") && u.searchParams.get("task") === "regression",
          ),
      ).toBe(true),
    );
  });

  it("explains metrics on focus and closes with Escape", async () => {
    routes();
    render(<ModelComparisonView />);
    const [info] = await screen.findAllByRole("button", { name: "What is Recall (sensitivity)?" });
    fireEvent.focus(info);
    const tip = document.getElementById(info.getAttribute("aria-describedby")!)!;
    expect(tip).toHaveAttribute("role", "tooltip");
    expect(tip).toHaveTextContent("Share of students below the pass mark whom the model flagged.");
    expect(tip.className).toContain("fixed");
    fireEvent.keyDown(info, { key: "Escape" });
    expect(tip.className).toContain("sr-only");
  });

  it("shows an actionable message when models are missing", async () => {
    mockFetch({
      "/models/evaluations": () =>
        json({ code: "models_unavailable", detail: "No training run." }, 503),
      "/models/selected": () =>
        json({ code: "models_unavailable", detail: "No training run." }, 503),
      "/models/scenario-comparison": () => json({ code: "models_unavailable", detail: "x" }, 503),
      "/models/cohort-comparison": () => json({ code: "models_unavailable", detail: "x" }, 503),
    });
    render(<ModelComparisonView />);
    expect(await screen.findByText("The models have not been trained")).toBeInTheDocument();
  });
});

describe("ModelComparisonView accessibility", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("has no axe violations once data is shown", async () => {
    routes();
    const { container } = render(<ModelComparisonView />);
    await screen.findByText("Fixture selection reason.");
    await expectNoAxeViolations(container);
  });
});
