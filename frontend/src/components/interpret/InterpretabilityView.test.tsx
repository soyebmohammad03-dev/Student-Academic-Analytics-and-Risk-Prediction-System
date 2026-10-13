import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  explanationFixture,
  json,
  mockFetch,
  postedBodies,
  recordsFixture,
  schemaFixture,
  summaryFixture,
} from "@/test/api";

import { InterpretabilityView } from "./InterpretabilityView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

function importance(url: URL) {
  const task = url.searchParams.get("task");
  const scenario = url.searchParams.get("scenario");
  const method = (label: string, value: number) => ({
    cohort: url.searchParams.get("cohort"),
    task,
    scenario,
    model: "fixture",
    model_label: "Fixture model",
    method: "permutation_test",
    method_label: label,
    data: "Test set, n = 8.",
    unit: "fixture unit",
    items: [
      {
        feature: "failures",
        attribute: "failures",
        label: "Past class failures",
        value,
        std: 0.02,
        rank: 1,
      },
      { feature: "sex", attribute: "sex", label: "Sex", value: 0, std: 0, rank: 2 },
    ],
    limitations: [`${label} limitation.`],
  });
  return {
    cohort: url.searchParams.get("cohort"),
    task,
    scenario,
    model: "fixture",
    model_label: `Fixture model (${task}, ${scenario})`,
    methods: [method("Permutation importance", 0.12), method("Mean |Shapley|", 0.3)],
    calibration: null,
  };
}

function routes() {
  return mockFetch({
    "/interpretability/importance": (url) => json(importance(url)),
    "/dataset/schema": (url) => json(schemaFixture(url.searchParams.get("cohort")!)),
    "/dataset/summary": (url) => json(summaryFixture(url.searchParams.get("cohort")!)),
    "/dataset/records": (url) =>
      json(recordsFixture(url.searchParams.get("cohort")!, Number(url.searchParams.get("page")))),
    "/interpretability/explain": (_url, init) =>
      json(explanationFixture(JSON.parse(String(init!.body)))),
    "/interpretability/sensitivity": (_url, init) => {
      const body = JSON.parse(String(init!.body));
      return json({
        kind: "model_sensitivity",
        cohort: body.cohort,
        task: body.task,
        scenario: body.scenario,
        model: "fixture",
        attribute: body.attribute,
        label: `Fixture ${body.attribute}`,
        output: "fixture output",
        points: [
          {
            value: "1",
            label: "1 (low)",
            current: true,
            output: 0.4,
            predicted_grade: null,
            at_risk: true,
            support: 30,
            sparse: false,
          },
          {
            value: "4",
            label: "4 (high)",
            current: false,
            output: 0.2,
            predicted_grade: null,
            at_risk: false,
            support: 3,
            sparse: true,
          },
        ],
        note: "Fixture sensitivity note.",
      });
    },
    "/interpretability/scenario-sensitivity": (_url, init) => {
      const body = JSON.parse(String(init!.body));
      return json({
        kind: "model_sensitivity",
        cohort: body.cohort,
        task: body.task,
        items: [
          {
            scenario: "early",
            model: "a",
            model_label: "Fixture early model",
            output: 0.3,
            predicted_grade: null,
            at_risk: true,
          },
        ],
        skipped: [],
        note: "Fixture scenario note.",
      });
    },
  });
}

describe("InterpretabilityView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows each importance method on its own card with its limitations", async () => {
    routes();
    render(<InterpretabilityView />);

    expect(await screen.findByRole("list", { name: "Permutation importance" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Mean |Shapley|" })).toBeInTheDocument();
    // Zero-valued (unused) attributes are not drawn.
    expect(screen.queryByTitle("Sex")).not.toBeInTheDocument();
    expect(screen.getByText("Permutation importance limitation.")).toBeInTheDocument();
  });

  it("requests importance for the chosen task and scenario", async () => {
    const fetchMock = routes();
    render(<InterpretabilityView />);
    await screen.findByText("Fixture model (classification, early)");

    fireEvent.click(screen.getByRole("radio", { name: "Final grade" }));
    fireEvent.click(screen.getByRole("radio", { name: "Full history" }));

    expect(await screen.findByText("Fixture model (regression, full_history)")).toBeInTheDocument();
    const urls = fetchMock.mock.calls.map(([u]) => new URL(u));
    const last = urls.filter((u) => u.pathname.endsWith("/importance")).at(-1)!;
    expect(last.searchParams.get("task")).toBe("regression");
    expect(last.searchParams.get("scenario")).toBe("full_history");
  });

  it("explains a record with only the scenario's inputs", async () => {
    const fetchMock = routes();
    render(<InterpretabilityView />);

    expect(await screen.findByText("Fixture reading.")).toBeInTheDocument();
    const [early] = postedBodies(fetchMock, "/interpretability/explain");
    expect(early.features).toEqual({ sex: "F", absences: 4 });

    fireEvent.click(screen.getByRole("radio", { name: "Mid-year" }));
    await waitFor(() =>
      expect(postedBodies(fetchMock, "/interpretability/explain")).toHaveLength(2),
    );
    const mid = postedBodies(fetchMock, "/interpretability/explain")[1];
    expect(mid.features).toEqual({ sex: "F", absences: 4, G1: 9 });

    // Scenario sensitivity may use both period grades, never the final grade.
    for (const body of postedBodies(fetchMock, "/interpretability/scenario-sensitivity")) {
      expect(body.features).not.toHaveProperty("G3");
    }
  });

  it("runs the sensitivity experiment for the chosen attribute and marks sparse values", async () => {
    const fetchMock = routes();
    render(<InterpretabilityView />);
    expect(await screen.findByText("Fixture studytime: model response")).toBeInTheDocument();
    expect(screen.getByText("sparse")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Vary"), { target: { value: "absences" } });
    expect(await screen.findByText("Fixture absences: model response")).toBeInTheDocument();
    expect(postedBodies(fetchMock, "/interpretability/sensitivity").at(-1)!.attribute).toBe(
      "absences",
    );
  });

  it("moves between records", async () => {
    const fetchMock = routes();
    render(<InterpretabilityView />);
    await screen.findByText("Row 1 of 40");
    fireEvent.click(screen.getByRole("button", { name: "Next row" }));
    expect(await screen.findByText("Row 2 of 40")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        fetchMock.mock.calls
          .map(([u]) => new URL(u))
          .some((u) => u.pathname.endsWith("/records") && u.searchParams.get("page") === "2"),
      ).toBe(true),
    );
  });

  it("explains how to produce missing interpretability results", async () => {
    mockFetch({
      "/interpretability/importance": () =>
        json({ code: "models_unavailable", detail: "No interpretability results." }, 503),
      "/dataset/schema": () => json(schemaFixture()),
      "/dataset/summary": () => json(summaryFixture()),
      "/dataset/records": () => new Promise<Response>(() => {}) as never,
    });
    render(<InterpretabilityView />);
    expect(await screen.findByText("The models have not been trained")).toBeInTheDocument();
  });
});

describe("sensitivity scale", () => {
  it("never stretches tiny differences: fixed domains per output type", async () => {
    const { outputDomain } = await import("./SensitivityChart");
    const base = { points: [{ output: 0.7169 }, { output: 0.7168 }] } as never;
    expect(
      outputDomain({
        ...(base as object),
        task: "classification",
        output: "model probability",
      } as never),
    ).toEqual([0, 1]);
    expect(
      outputDomain({ ...(base as object), task: "regression", output: "predicted G3" } as never),
    ).toEqual([0, 20]);
    const [lo, hi] = outputDomain({
      task: "classification",
      output: "decision score",
      points: [{ output: -0.13 }, { output: -0.12 }],
    } as never);
    expect(hi - lo).toBe(2);
    expect(lo).toBeLessThan(-0.13);
  });
});
