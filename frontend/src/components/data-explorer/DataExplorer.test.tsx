import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Cohort } from "@/lib/api";

import { DataExplorer } from "./DataExplorer";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

// Fixture responses shaped like the API. Values are test data, not dataset results.
const ROWS: Record<Cohort, number> = { math: 30, portuguese: 12 };

function summary(cohort: Cohort) {
  return {
    cohort,
    subject: cohort === "math" ? "Mathematics" : "Portuguese language",
    filename: cohort === "math" ? "student-mat.csv" : "student-por.csv",
    source: {
      name: "UCI Student Performance (ID 320)",
      url: "https://x",
      license: "CC BY 4.0",
      citation: "",
    },
    rows: ROWS[cohort],
    columns: 2,
    numerical_columns: 1,
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

function quality(cohort: Cohort) {
  return {
    cohort,
    status: "pass",
    rows: ROWS[cohort],
    columns: 2,
    missing_values: 0,
    duplicate_rows: 0,
    invalid_values: 0,
    checks: [
      {
        key: "missing",
        title: "Missing values",
        status: "pass",
        summary: "Every cell has a value.",
        affected: 0,
      },
    ],
    observations: [],
    column_issues: [],
  };
}

function schema(cohort: Cohort) {
  return {
    cohort,
    source: "",
    columns: [
      {
        name: "school",
        position: 1,
        label: "School",
        description: "Student's school.",
        group: "Demographic",
        measure: "categorical",
        scale: "binary",
        role: "feature",
        dtype: "string",
        allowed_values: [{ code: "GP", label: "Gabriel Pereira" }],
        minimum: null,
        maximum: null,
        notes: [],
        observed: { missing: 0, invalid: 0, unique: 1, minimum: null, maximum: null },
      },
      {
        name: "G3",
        position: 33,
        label: "Final grade",
        description: "Final grade.",
        group: "Grades",
        measure: "numerical",
        scale: "grade",
        role: "target",
        dtype: "integer",
        allowed_values: [],
        minimum: 0,
        maximum: 20,
        notes: [],
        observed: { missing: 0, invalid: 0, unique: 5, minimum: 4, maximum: 18 },
      },
    ],
  };
}

function records(url: URL) {
  const cohort = url.searchParams.get("cohort") as Cohort;
  const page = Number(url.searchParams.get("page"));
  const size = Number(url.searchParams.get("page_size"));
  const search = url.searchParams.get("search");
  const all = Array.from({ length: ROWS[cohort] }, (_, i) => ({
    row: i + 1,
    values: { school: i === 4 ? "MS" : "GP", G3: i % 20 },
  }));
  const matching = search ? all.filter((r) => r.values.school.toLowerCase().includes(search)) : all;
  return {
    cohort,
    page,
    page_size: size,
    total: matching.length,
    total_pages: Math.max(1, Math.ceil(matching.length / size)),
    search,
    columns: ["school", "G3"],
    items: matching.slice((page - 1) * size, page * size),
  };
}

const overlap = {
  method: "Matched on 13 attributes.",
  match_attributes: ["school"],
  math_rows: 30,
  portuguese_rows: 12,
  join_pairs: 3,
  math_rows_matched: 3,
  portuguese_rows_matched: 3,
  unambiguous_matches: 2,
  ambiguous_profiles: 1,
  caveat: "Matching is approximate.",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function mockApi() {
  const fetchMock = vi.fn((input: string) => {
    const url = new URL(input);
    const cohort = url.searchParams.get("cohort") as Cohort;
    const resource = url.pathname.split("/").pop();
    const body =
      resource === "summary"
        ? summary(cohort)
        : resource === "quality"
          ? quality(cohort)
          : resource === "schema"
            ? schema(cohort)
            : resource === "records"
              ? records(url)
              : overlap;
    return Promise.resolve(json(body));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function requestedUrls(fetchMock: ReturnType<typeof mockApi>, resource: string) {
  return fetchMock.mock.calls
    .map(([input]) => new URL(input))
    .filter((url) => url.pathname.endsWith(`/dataset/${resource}`));
}

describe("DataExplorer", () => {
  beforeEach(() => window.history.replaceState(null, "", "/data-explorer"));
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("renders the overview, quality, records and dictionary from the API", async () => {
    mockApi();
    render(<DataExplorer />);

    expect(await screen.findByRole("heading", { name: "Mathematics" })).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("All 1 checks passed")).toBeInTheDocument();
    expect(await screen.findByText("Rows 1–25 of 30")).toBeInTheDocument();
    expect(screen.getByText("Student's school.")).toBeInTheDocument();
    expect(await screen.findByText("Likely the same student in both files")).toBeInTheDocument();
  });

  it("switches cohort, refetches and updates the URL", async () => {
    const fetchMock = mockApi();
    render(<DataExplorer />);
    await screen.findByRole("heading", { name: "Mathematics" });

    fireEvent.click(screen.getByRole("radio", { name: "Portuguese" }));

    expect(await screen.findByRole("heading", { name: "Portuguese language" })).toBeInTheDocument();
    expect(await screen.findByText("Rows 1–12 of 12")).toBeInTheDocument();
    expect(window.location.search).toBe("?cohort=portuguese");
    expect(requestedUrls(fetchMock, "summary").map((u) => u.searchParams.get("cohort"))).toEqual([
      "math",
      "portuguese",
    ]);
  });

  it("reads the initial cohort from the URL", async () => {
    window.history.replaceState(null, "", "/data-explorer?cohort=portuguese");
    mockApi();
    render(<DataExplorer />);

    expect(await screen.findByRole("heading", { name: "Portuguese language" })).toBeInTheDocument();
  });

  it("paginates records", async () => {
    const fetchMock = mockApi();
    render(<DataExplorer />);
    await screen.findByText("Rows 1–25 of 30");

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    expect(await screen.findByText("Rows 26–30 of 30")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(requestedUrls(fetchMock, "records").at(-1)?.searchParams.get("page")).toBe("2");
  });

  it("searches after typing pauses and shows an empty state", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = mockApi();
    render(<DataExplorer />);
    await screen.findByText("Rows 1–25 of 30");
    const input = screen.getByRole("searchbox", { name: "Search records" });

    fireEvent.change(input, { target: { value: "ms" } });
    await act(() => vi.advanceTimersByTimeAsync(300));

    expect(await screen.findByText("1 matching student")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByRole("rowheader", { name: "5" })).toBeInTheDocument();
    expect(requestedUrls(fetchMock, "records").at(-1)?.searchParams.get("search")).toBe("ms");

    fireEvent.change(input, { target: { value: "nothing" } });
    await act(() => vi.advanceTimersByTimeAsync(300));

    expect(await screen.findByText("No students match “nothing”")).toBeInTheDocument();
  });

  it("explains how to fix a missing dataset", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(json({ code: "dataset_unavailable", detail: "not found" }, 503))),
    );
    render(<DataExplorer />);

    expect(await screen.findByText("The dataset has not been downloaded")).toBeInTheDocument();
    expect(screen.getByText(/python -m analytics\.data\.download/)).toBeInTheDocument();
  });

  it("explains when the API is offline and retries", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );
    render(<DataExplorer />);
    expect(await screen.findByText("The analytics API is not reachable")).toBeInTheDocument();

    mockApi();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("heading", { name: "Mathematics" })).toBeInTheDocument();
  });
});
