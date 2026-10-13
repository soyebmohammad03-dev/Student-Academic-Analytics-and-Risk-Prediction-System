import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RiskAnalysisView } from "./RiskAnalysisView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

// Hand-written fixtures shaped like the API. Values are test data, not dataset results.
const interval = (low: number, high: number) => ({ low, high, confidence: 0.95 });

function profiles(cohort: string) {
  return {
    kind: "group_statistics",
    cohort,
    n: 40,
    at_risk: 10,
    risk_percent: 25,
    risk_ci: interval(0.14, 0.4),
    threshold: 10,
    single: [
      {
        variable: "failures",
        label: "Past class failures",
        groups: [
          {
            key: "0",
            label: "None",
            n: 32,
            at_risk: 6,
            risk_percent: 18.75,
            risk_ci: interval(0.09, 0.35),
            difference_from_overall: -6.25,
            reliable: true,
          },
          {
            key: "1",
            label: "1",
            n: 8,
            at_risk: 4,
            risk_percent: 50,
            risk_ci: interval(0.22, 0.78),
            difference_from_overall: 25,
            reliable: false,
          },
        ],
        test: "Fisher's exact test",
        p: 0.08,
        p_adjusted: 0.16,
        cramers_v: 0.27,
        magnitude: "small",
        warnings: [],
      },
    ],
    pairs: [],
    notes: ["Fixture note about groups, not individuals."],
  };
}

function importance(url: URL) {
  const task = url.searchParams.get("task");
  return {
    cohort: url.searchParams.get("cohort"),
    task,
    scenario: url.searchParams.get("scenario"),
    model: "logistic_regression",
    model_label: `Fixture model (${task})`,
    methods: [
      {
        cohort: "math",
        task,
        scenario: "early",
        model: "logistic_regression",
        model_label: "Fixture model",
        method: "permutation_test",
        method_label: "Permutation importance (held-out test set)",
        data: "Test set, n = 8.",
        unit: "decrease in test ROC-AUC",
        items: [
          {
            feature: "failures",
            attribute: "failures",
            label: "Past class failures",
            value: 0.12,
            std: 0.02,
            rank: 1,
          },
          { feature: "sex", attribute: "sex", label: "Sex", value: 0, std: 0, rank: 2 },
        ],
        limitations: ["Fixture limitation."],
      },
    ],
    calibration: null,
  };
}

function mockApi(overrides: Record<string, () => Response> = {}) {
  const fetchMock = vi.fn((input: string) => {
    const url = new URL(input);
    const resource = url.pathname.split("/").pop()!;
    if (overrides[resource]) return Promise.resolve(overrides[resource]());
    return Promise.resolve(
      json(resource === "profiles" ? profiles(url.searchParams.get("cohort")!) : importance(url)),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("RiskAnalysisView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders group profiles and importance from the API", async () => {
    mockApi();
    render(<RiskAnalysisView />);

    expect(
      await screen.findByRole("list", { name: "Academic risk by Past class failures" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("10 of 40 students (25.0%) had a final grade below 10."),
    ).toBeInTheDocument();
    expect(screen.getByText(/few/)).toBeInTheDocument();
    expect(
      await screen.findByRole("list", { name: "Permutation importance (held-out test set)" }),
    ).toBeInTheDocument();
    // Zero-valued (unused) features are not drawn.
    expect(screen.queryByTitle("Sex")).not.toBeInTheDocument();
    expect(screen.getByText("Fixture limitation.")).toBeInTheDocument();
  });

  it("requests importance for the chosen task and scenario", async () => {
    const fetchMock = mockApi();
    render(<RiskAnalysisView />);
    await screen.findByText("Fixture model (classification)");

    fireEvent.click(screen.getByRole("radio", { name: "Final grade" }));
    fireEvent.click(screen.getByRole("radio", { name: "Full history" }));

    expect(await screen.findByText("Fixture model (regression)")).toBeInTheDocument();
    const last = new URL(fetchMock.mock.calls.at(-1)![0]);
    expect(last.searchParams.get("task")).toBe("regression");
    expect(last.searchParams.get("scenario")).toBe("full_history");
  });

  it("explains how to produce missing models", async () => {
    mockApi({
      importance: () =>
        json({ code: "models_unavailable", detail: "No interpretability results." }, 503),
    });
    render(<RiskAnalysisView />);

    expect(await screen.findByText("The models have not been trained")).toBeInTheDocument();
    expect(screen.getByText(/analytics\.interpret\.build/)).toBeInTheDocument();
  });

  it("shows loading states before data arrives", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    render(<RiskAnalysisView />);
    expect(screen.getByLabelText("Loading risk profiles")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading feature importance")).toBeInTheDocument();
  });
});
