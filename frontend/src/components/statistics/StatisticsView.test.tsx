import { fireEvent, render, screen } from "@testing-library/react";
import { expectNoAxeViolations } from "@/test/axe";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { statisticsResponse } from "@/test/statisticsFixtures";

import { StatisticsView } from "./StatisticsView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function mockApi() {
  const fetchMock = vi.fn((input: string) => {
    const url = new URL(input);
    return Promise.resolve(json(statisticsResponse(url.pathname, url.searchParams.get("cohort")!)));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("StatisticsView", () => {
  beforeEach(() => window.history.replaceState(null, "", "/statistics"));
  afterEach(() => vi.unstubAllGlobals());

  it("shows loading placeholders before data arrives", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    const { container } = render(<StatisticsView />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("renders API results with adjusted p-values and effect sizes", async () => {
    mockApi();
    render(<StatisticsView />);

    expect(
      await screen.findByText("Is weekly study time associated with final performance (G3)?"),
    ).toBeInTheDocument();
    expect(screen.getByText("Significant after correction")).toBeInTheDocument();
    expect(screen.getByText("30.0%")).toBeInTheDocument();
    expect(await screen.findByText("Welch's t-test")).toBeInTheDocument();
    expect(
      screen.getByText(/Statistical significance indicates an association/),
    ).toBeInTheDocument();
  });

  it("requests the selected comparison variable and cohort", async () => {
    const fetchMock = mockApi();
    render(<StatisticsView />);
    await screen.findByText("Welch's t-test");

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "Medu" } });
    fireEvent.click(screen.getByRole("radio", { name: "Portuguese" }));

    const urls = fetchMock.mock.calls.map(([u]) => new URL(u));
    expect(urls.some((u) => u.searchParams.get("variable") === "Medu")).toBe(true);
    expect(urls.some((u) => u.searchParams.get("cohort") === "portuguese")).toBe(true);
  });

  it("explains a missing dataset", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(json({ code: "dataset_unavailable", detail: "x" }, 503))),
    );
    render(<StatisticsView />);
    expect(await screen.findByText("The dataset has not been downloaded")).toBeInTheDocument();
  });
});

describe("StatisticsView accessibility", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("has no axe violations once data is shown", async () => {
    mockApi();
    const { container } = render(<StatisticsView />);
    await screen.findByText("Welch's t-test");
    await expectNoAxeViolations(container);
  });
});
