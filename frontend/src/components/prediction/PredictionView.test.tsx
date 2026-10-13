import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  explanationFixture,
  interval,
  json,
  mockFetch,
  postedBodies,
  predictionFixture,
  recordsFixture,
  schemaFixture,
  summaryFixture,
} from "@/test/api";

import { PredictionView } from "./PredictionView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

function routes() {
  return mockFetch({
    "/dataset/schema": (url) => json(schemaFixture(url.searchParams.get("cohort")!)),
    "/dataset/summary": (url) => json(summaryFixture(url.searchParams.get("cohort")!)),
    "/dataset/records": (url) =>
      json(recordsFixture(url.searchParams.get("cohort")!, Number(url.searchParams.get("page")))),
    "/models/predict": (_url, init) => json(predictionFixture(JSON.parse(String(init!.body)))),
    "/interpretability/explain": (_url, init) =>
      json(explanationFixture(JSON.parse(String(init!.body)))),
    "/risk/insights": (_url, init) => {
      const body = JSON.parse(String(init!.body));
      return json({
        individual: explanationFixture({ ...body, task: "classification" }),
        group: [
          {
            kind: "group_statistics",
            variable: "absences",
            label: "Absence band",
            group: "1–10",
            n: 20,
            risk_percent: 30,
            risk_ci: interval(0.15, 0.5),
            reliable: true,
            cohort_risk_percent: 25,
          },
        ],
        suggestions: {
          cohort: body.cohort,
          suggestions: [],
          not_shown: [],
          disclaimer: "Fixture disclaimer.",
        },
        reading: [],
      });
    },
  });
}

async function fill(scenarioGrades: Record<string, string> = {}) {
  fireEvent.change(await screen.findByLabelText("Sex"), { target: { value: "F" } });
  fireEvent.change(screen.getByLabelText("School absences"), { target: { value: "4" } });
  for (const [label, value] of Object.entries(scenarioGrades)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
}

describe("PredictionView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("never offers the final grade, and shows period grades only where allowed", async () => {
    routes();
    render(<PredictionView />);
    await screen.findByLabelText("Sex");

    expect(screen.queryByLabelText("Final grade")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("First period grade")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Mid-year" }));
    expect(screen.getByLabelText("First period grade")).toBeInTheDocument();
    expect(screen.queryByLabelText("Second period grade")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Full history" }));
    expect(screen.getByLabelText("Second period grade")).toBeInTheDocument();
    expect(screen.queryByLabelText("Final grade")).not.toBeInTheDocument();
  });

  it("validates before submitting and sends nothing when invalid", async () => {
    const fetchMock = routes();
    render(<PredictionView />);
    fireEvent.change(await screen.findByLabelText("School absences"), {
      target: { value: "120" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Predict" }));

    expect(await screen.findByText("Must be at most 93.")).toBeInTheDocument();
    expect(screen.getByText("Required.")).toBeInTheDocument();
    expect(screen.getByLabelText("School absences")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("2 fields need attention.")).toBeInTheDocument();
    // Focus moves to the first invalid field on screen (school factors come before demographics).
    expect(screen.getByLabelText("School absences")).toHaveFocus();
    expect(postedBodies(fetchMock, "/models/predict")).toHaveLength(0);
  });

  it("sends only the scenario's inputs and shows both tasks separately", async () => {
    const fetchMock = routes();
    render(<PredictionView />);
    fireEvent.click(await screen.findByRole("radio", { name: "Mid-year" }));
    await fill({ "First period grade": "9" });
    fireEvent.click(screen.getByRole("button", { name: "Predict" }));

    expect(await screen.findByText("Predicted final grade")).toBeInTheDocument();
    expect(screen.getByText("8.4")).toBeInTheDocument();
    expect(screen.getByText("Flagged: final grade below 10 predicted")).toBeInTheDocument();
    // The SVM has no probability: say so instead of inventing one.
    expect(screen.getByText(/No probability is available/)).toBeInTheDocument();

    const bodies = postedBodies(fetchMock, "/models/predict");
    expect(bodies.map((b) => b.task).sort()).toEqual(["classification", "regression"]);
    for (const body of bodies) {
      expect(body.scenario).toBe("mid_year");
      expect(body.features).toEqual({ sex: "F", absences: 4, G1: 9 });
    }
    expect(await screen.findByText("Absence band:", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Fixture disclaimer.")).toBeInTheDocument();
  });

  it("loads a dataset record without its final grade", async () => {
    const fetchMock = routes();
    render(<PredictionView />);
    await screen.findByLabelText("Sex");
    fireEvent.click(screen.getByRole("button", { name: "Load record" }));

    await waitFor(() => expect(screen.getByLabelText("School absences")).toHaveValue(4));
    expect(screen.getByText(/Its final grade is not loaded/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Predict" }));

    await screen.findByText("Predicted final grade");
    for (const body of postedBodies(fetchMock, "/models/predict")) {
      expect(body.features).toEqual({ sex: "F", absences: 4 });
      expect(body.features).not.toHaveProperty("G3");
    }
  });

  it("clears results when the scenario changes, so they never mix", async () => {
    routes();
    render(<PredictionView />);
    await fill();
    fireEvent.click(screen.getByRole("button", { name: "Predict" }));
    await screen.findByText("Predicted final grade");

    fireEvent.click(screen.getByRole("radio", { name: "Mid-year" }));
    expect(screen.queryByText("Predicted final grade")).not.toBeInTheDocument();
  });

  it("marks results as outdated after an input changes", async () => {
    routes();
    render(<PredictionView />);
    await fill();
    fireEvent.click(screen.getByRole("button", { name: "Predict" }));
    await screen.findByText("Predicted final grade");

    fireEvent.change(screen.getByLabelText("School absences"), { target: { value: "5" } });
    expect(screen.getByText("Inputs changed")).toBeInTheDocument();
  });

  it("reports an API rejection without inventing a result", async () => {
    mockFetch({
      "/dataset/schema": () => json(schemaFixture()),
      "/dataset/summary": () => json(summaryFixture()),
      "/models/predict": () =>
        json({ code: "invalid_record", detail: "Fixture: undocumented value." }, 422),
      "/interpretability/explain": () =>
        json({ code: "invalid_record", detail: "Fixture: undocumented value." }, 422),
      "/risk/insights": () =>
        json({ code: "invalid_record", detail: "Fixture: undocumented value." }, 422),
    });
    render(<PredictionView />);
    await fill();
    fireEvent.click(screen.getByRole("button", { name: "Predict" }));

    expect((await screen.findAllByText("Fixture: undocumented value.")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Predicted final grade")).not.toBeInTheDocument();
  });

  it("shows the educational-use disclaimer", async () => {
    routes();
    render(<PredictionView />);
    expect(screen.getByText("For educational analysis only")).toBeInTheDocument();
    expect(screen.getByText(/not dropout/)).toBeInTheDocument();
  });
});
