import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { interval, json, mockFetch } from "@/test/api";

import { DashboardView } from "./DashboardView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const components = (status: "available" | "unavailable") => [
  { key: "api", label: "API", status: "available", detail: "Operational.", action: null },
  {
    key: "dataset",
    label: "Dataset",
    status,
    detail: status === "available" ? "Fixture files verified." : "Fixture files missing.",
    action: status === "available" ? null : "python -m analytics.data.download",
  },
  { key: "models", label: "Trained models", status, detail: "Fixture models.", action: null },
];

function overview(cohort: "math" | "portuguese", n: number, atRisk: number) {
  return {
    cohort,
    subject: cohort === "math" ? "Mathematics" : "Portuguese language",
    rows: n,
    columns: 33,
    validation_status: "pass",
    missing_values: 0,
    duplicate_rows: 0,
    invalid_values: 0,
    final_grade: { n, mean: 10.5, median: 11, std: 4, minimum: 0, maximum: 20, zero_count: 3 },
    observed_risk: {
      kind: "observed_historical",
      definition: "Fixture definition: observed, not a prediction.",
      n,
      at_risk: atRisk,
      percent: (100 * atRisk) / n,
      ci: interval(0.2, 0.4),
    },
  };
}

function dashboard() {
  return {
    status: "ready",
    components: components("available"),
    dataset: {
      available: true,
      detail: "ok",
      cohorts: [overview("math", 40, 12), overview("portuguese", 60, 9)],
    },
    models: {
      available: true,
      detail: "ok",
      trained_at: "2026-01-01T00:00:00+00:00",
      selected: [
        {
          kind: "model_evaluation",
          cohort: "math",
          task: "classification",
          scenario: "early",
          model: "svm",
          label: "Fixture SVM",
          metric: "f1",
          cv_mean: 0.41,
          cv_std: 0.03,
          test: 0.47,
        },
      ],
    },
    notes: ["Fixture note: observed figures are not predictions."],
  };
}

function routes(body: unknown = dashboard()) {
  return mockFetch({
    "/dashboard/summary": () => json(body),
    "/statistics/distributions": (url) =>
      json({
        cohort: url.searchParams.get("cohort"),
        grades: [
          {
            variable: "G3",
            counts: [
              { value: 0, count: 3 },
              { value: 12, count: 20 },
            ],
          },
        ],
      }),
    "/statistics/hypothesis-tests": (url) =>
      json({
        cohort: url.searchParams.get("cohort"),
        alpha: 0.05,
        correction: "Fixture correction",
        items: [
          {
            key: "RQ2",
            question: "Fixture question about past failures?",
            evidence: "confirmatory",
            p_adjusted: 0.001,
            significant: true,
            effect: { name: "Cohen's d", value: 0.9, ci: null, magnitude: "large" },
          },
        ],
      }),
    "/pipeline/summary": (url) =>
      json({
        cohort: url.searchParams.get("cohort"),
        scenario: url.searchParams.get("scenario"),
        steps: [],
        overview: null,
        scenario_features: [],
        research_questions: [],
        eda_charts: {},
        selected_models: [],
        top_attributes: { classification: ["Past class failures"], regression: ["Absences"] },
        risk_profile_highlights: ["Fixture highlight."],
      }),
  });
}

describe("DashboardView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows observed cohort figures from the API, labelled as observed", async () => {
    routes();
    render(<DashboardView />);

    expect(await screen.findByRole("heading", { name: "Mathematics" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Portuguese language" })).toBeInTheDocument();
    expect(screen.getByText("30.0%")).toBeInTheDocument();
    expect(screen.getByText(/12 of 40/)).toBeInTheDocument();
    expect(screen.getAllByText("Observed · historical data").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Fixture note: observed figures are not predictions."),
    ).toBeInTheDocument();
  });

  it("separates model evaluation, with test and CV scores and no invented cells", async () => {
    routes();
    render(<DashboardView />);

    const table = await screen.findByRole("table", { name: /Selected model per cohort/ });
    expect(within(table).getByText("Fixture SVM")).toBeInTheDocument();
    expect(within(table).getByText("0.47")).toBeInTheDocument();
    expect(within(table).getByText("CV 0.41 ± 0.03")).toBeInTheDocument();
    // Cells without a selected model show a dash rather than a value.
    expect(within(table).getAllByText("—").length).toBe(11);
    expect(screen.getAllByText("Model evaluation").length).toBeGreaterThan(0);
  });

  it("shows findings with significance and effect size", async () => {
    routes();
    render(<DashboardView />);
    expect(await screen.findByText("Fixture question about past failures?")).toBeInTheDocument();
    expect(screen.getByText(/Cohen's d 0.90 \(large\)/)).toBeInTheDocument();
    expect(await screen.findByText("Fixture highlight.")).toBeInTheDocument();
    expect(screen.getByText("Past class failures")).toBeInTheDocument();
  });

  it("reports a missing dataset with its command instead of figures", async () => {
    const body = dashboard();
    routes({
      ...body,
      status: "degraded",
      components: components("unavailable"),
      dataset: { available: false, detail: "Fixture files missing.", cohorts: [] },
      models: { ...body.models, available: false, detail: "No models.", selected: [] },
    });
    render(<DashboardView />);

    expect(await screen.findByText("The dataset is not available")).toBeInTheDocument();
    expect(screen.getByText("Some results are unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("python -m analytics.data.download").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Mathematics" })).not.toBeInTheDocument();
  });

  it("explains how to start the API when it is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );
    render(<DashboardView />);
    expect(await screen.findByText("The analytics API is not reachable")).toBeInTheDocument();
  });
});
