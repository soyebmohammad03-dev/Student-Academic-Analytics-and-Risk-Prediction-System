import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { statisticsResponse } from "@/test/statisticsFixtures";

import { EdaView } from "./EdaView";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("EdaView", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders every chart type from the API with data tables", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        const url = new URL(input);
        return Promise.resolve(
          json(statisticsResponse(url.pathname, url.searchParams.get("cohort")!)),
        );
      }),
    );
    render(<EdaView />);

    expect(
      await screen.findByRole("img", { name: "Histogram of Final grade" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Distribution of Sex" })).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Box plots of G3 by Weekly study time" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Scatter plot of Final grade/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Correlation heatmap" })).toBeInTheDocument();
    expect(screen.getAllByText("Show data").length).toBeGreaterThanOrEqual(5);
    expect(screen.getByText("Below 10 (academic risk)")).toBeInTheDocument();
    expect(screen.getByText("12.40")).toBeInTheDocument(); // risk profile value
  });

  it("shows loading and offline states", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("offline"))),
    );
    render(<EdaView />);

    expect(screen.getByLabelText("Loading charts")).toBeInTheDocument();
    expect(await screen.findByText("The analytics API is not reachable")).toBeInTheDocument();
  });
});
