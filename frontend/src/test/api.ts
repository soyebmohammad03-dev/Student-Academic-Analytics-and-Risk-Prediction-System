/**
 * Test helpers: a routed fetch mock and small hand-written fixtures shaped like the
 * API. Fixture values are test data, not dataset results.
 */
import { vi } from "vitest";

import type { ColumnInfo } from "@/lib/api";

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

export type Route = (url: URL, init?: RequestInit) => Response | Promise<Response>;

/** Stub fetch; each request is answered by the route whose key ends the pathname. */
export function mockFetch(routes: Record<string, Route>) {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    const url = new URL(input);
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => url.pathname.endsWith(k));
    if (!key) return Promise.resolve(json({ code: "not_found", detail: url.pathname }, 404));
    return Promise.resolve(routes[key](url, init));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Bodies of POST requests sent to a path. */
export function postedBodies(fetchMock: ReturnType<typeof mockFetch>, path: string) {
  return fetchMock.mock.calls
    .filter(([input, init]) => new URL(input).pathname.endsWith(path) && init?.method === "POST")
    .map(([, init]) => JSON.parse(String(init!.body)) as Record<string, unknown>);
}

export const interval = (low: number, high: number) => ({ low, high, confidence: 0.95 });

function column(
  name: string,
  overrides: Partial<ColumnInfo> & Pick<ColumnInfo, "label" | "group">,
): ColumnInfo {
  return {
    name,
    position: 0,
    description: overrides.label,
    measure: "categorical",
    scale: "binary",
    role: "feature",
    dtype: "string",
    allowed_values: [],
    minimum: null,
    maximum: null,
    notes: [],
    observed: null,
    ...overrides,
  };
}

/** A reduced schema: two attributes, the period grades and the target. */
export function schemaFixture(cohort = "math") {
  return {
    cohort,
    source: "fixture.csv",
    columns: [
      column("sex", {
        label: "Sex",
        group: "Demographic",
        allowed_values: [
          { code: "F", label: "Female" },
          { code: "M", label: "Male" },
        ],
      }),
      column("absences", {
        label: "School absences",
        group: "School and study",
        measure: "numerical",
        scale: "count",
        dtype: "integer",
        minimum: 0,
        maximum: 93,
      }),
      ...["G1", "G2"].map((g) =>
        column(g, {
          label: g === "G1" ? "First period grade" : "Second period grade",
          group: "Grades",
          measure: "numerical",
          scale: "grade",
          role: "prior_grade",
          dtype: "integer",
          minimum: 0,
          maximum: 20,
        }),
      ),
      column("G3", {
        label: "Final grade",
        group: "Grades",
        measure: "numerical",
        scale: "grade",
        role: "target",
        dtype: "integer",
        minimum: 0,
        maximum: 20,
      }),
    ],
  };
}

export function summaryFixture(cohort = "math", rows = 40) {
  return {
    cohort,
    subject: cohort === "math" ? "Mathematics" : "Portuguese language",
    filename: "fixture.csv",
    source: { name: "UCI", url: "", license: "", citation: "" },
    rows,
    columns: 5,
    numerical_columns: 4,
    categorical_columns: 1,
    missing_values: 0,
    duplicate_rows: 0,
    invalid_values: 0,
    validation_status: "pass",
    target: {
      name: "G3",
      label: "Final grade",
      description: "",
      minimum: 0,
      maximum: 20,
      pass_mark: 10,
      prior_grades: ["G1", "G2"],
    },
  };
}

export function recordsFixture(cohort: string, row: number) {
  return {
    cohort,
    page: row,
    page_size: 1,
    total: 40,
    total_pages: 40,
    search: null,
    columns: ["sex", "absences", "G1", "G2", "G3"],
    items: [{ row, values: { sex: "F", absences: 4, G1: 9, G2: 8, G3: 7 } }],
  };
}

export function predictionFixture(body: Record<string, unknown>) {
  const classification = body.task === "classification";
  return {
    cohort: body.cohort,
    task: body.task,
    scenario: body.scenario,
    model: classification ? "svm" : "linear_regression",
    model_label: classification ? "Fixture SVM" : "Fixture linear model",
    predicted_grade: classification ? null : 8.4,
    raw_prediction: classification ? null : 8.4,
    at_risk: classification ? true : null,
    score: classification ? 0.31 : null,
    probability: null,
    score_kind: classification ? "decision_function" : null,
    threshold: classification ? 0 : null,
    model_test_metrics: classification
      ? { recall: 0.5, precision: 0.48, f1: 0.49 }
      : { mae: 3.1, rmse: 3.9, r2: 0.1 },
    trained_at: "2026-01-01T00:00:00+00:00",
    caveats: ["Fixture caveat."],
  };
}

export function explanationFixture(body: Record<string, unknown>) {
  return {
    prediction: predictionFixture(body),
    explanation: {
      kind: "individual_model_explanation",
      method: "Fixture method.",
      output: "fixture output",
      base_value: 0.1,
      prediction: 0.31,
      contributions: [
        {
          attribute: "absences",
          label: "School absences",
          value: "4",
          contribution: 0.2,
          standard_error: 0.01,
          direction: "raises",
        },
      ],
      other_attributes: 1,
      other_contribution: 0.01,
      n_samples: 16,
      background: "fixture background",
      background_size: 10,
      seed: 42,
      reading: "Fixture reading.",
      limitations: ["Fixture explanation limitation."],
    },
    score_percentile: body.task === "classification" ? 80 : null,
  };
}
