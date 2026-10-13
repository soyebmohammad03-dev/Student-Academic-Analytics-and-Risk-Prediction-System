import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expectNoAxeViolations } from "@/test/axe";
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

function classifiers(cohort: string) {
  const metrics = { recall: 0.5, precision: 0.4, f1: 0.44, roc_auc: 0.6 };
  return {
    cohort,
    task: "classification",
    primary_metric: "f1",
    rows: [
      {
        scenario: "early",
        label: "Early warning (no grades)",
        information: "Non-grade attributes only.",
        selected_model: "svm",
        selected_label: "Fixture classifier",
        best_cv_model: "svm",
        cv: metrics,
        cv_std: metrics,
        test: metrics,
        baseline_cv: metrics,
        baseline_test: metrics,
      },
    ],
    note: "Fixture note.",
  };
}

function mockApi(overrides: Record<string, () => Response> = {}) {
  const fetchMock = vi.fn((input: string) => {
    const url = new URL(input);
    const resource = url.pathname.split("/").pop()!;
    const cohort = url.searchParams.get("cohort")!;
    if (overrides[resource]) return Promise.resolve(overrides[resource]());
    return Promise.resolve(json(resource === "profiles" ? profiles(cohort) : classifiers(cohort)));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("RiskAnalysisView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders the definition and group profiles from the API", async () => {
    mockApi();
    render(<RiskAnalysisView />);

    expect(
      await screen.findByRole("list", { name: "Academic risk by Past class failures" }),
    ).toBeInTheDocument();
    expect(screen.getByText("25.0%")).toBeInTheDocument();
    expect(screen.getByText(/10 of 40/)).toBeInTheDocument();
    expect(screen.getAllByText(/not dropout/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/n = 8 · few/)).toBeInTheDocument();
    expect(screen.getByText("Fixture note about groups, not individuals.")).toBeInTheDocument();
  });

  it("keeps model-derived results apart from observed statistics", async () => {
    mockApi();
    render(<RiskAnalysisView />);

    expect(await screen.findByText("Fixture classifier")).toBeInTheDocument();
    expect(screen.getAllByText("Observed · historical data").length).toBeGreaterThan(0);
    expect(screen.getByText("Model evaluation")).toBeInTheDocument();
    const table = screen.getByRole("table", { name: /selected classifiers/ });
    expect(within(table).getByText("50%")).toBeInTheDocument();
  });

  it("does not use unsupported risk bands", async () => {
    mockApi();
    render(<RiskAnalysisView />);
    await screen.findByText("Fixture classifier");
    expect(screen.queryByText(/high risk/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/medium risk/i)).not.toBeInTheDocument();
  });

  it("explains how to produce missing models", async () => {
    mockApi({
      "scenario-comparison": () =>
        json({ code: "models_unavailable", detail: "No training run." }, 503),
    });
    render(<RiskAnalysisView />);

    expect(await screen.findByText("The models have not been trained")).toBeInTheDocument();
    expect(screen.getByText(/analytics\.ml\.train/)).toBeInTheDocument();
    // Observed profiles still render.
    expect(
      await screen.findByRole("list", { name: "Academic risk by Past class failures" }),
    ).toBeInTheDocument();
  });

  it("refetches for the chosen cohort", async () => {
    const fetchMock = mockApi();
    render(<RiskAnalysisView />);
    await screen.findByText("Fixture classifier");

    fireEvent.click(screen.getByRole("radio", { name: "Portuguese" }));
    await waitFor(() =>
      expect(new URL(fetchMock.mock.calls.at(-1)![0]).searchParams.get("cohort")).toBe(
        "portuguese",
      ),
    );
  });

  it("shows loading states before data arrives", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    render(<RiskAnalysisView />);
    expect(screen.getByLabelText("Loading risk profiles")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading classifier results")).toBeInTheDocument();
  });
});

describe("RiskAnalysisView accessibility", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("has no axe violations once data is shown", async () => {
    mockApi();
    const { container } = render(<RiskAnalysisView />);
    await screen.findByText("Fixture classifier");
    await expectNoAxeViolations(container);
  });
});
