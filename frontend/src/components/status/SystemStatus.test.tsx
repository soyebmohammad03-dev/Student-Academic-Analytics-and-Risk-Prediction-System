import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SystemStatus } from "./SystemStatus";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("SystemStatus", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows live API and dataset status when the backend responds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        Promise.resolve(
          url.endsWith("/health")
            ? jsonResponse({ status: "ok", version: "0.1.0", environment: "test" })
            : jsonResponse({
                name: "x",
                version: "0.1.0",
                dataset: { name: "UCI", source_url: "", available_locally: false },
                modules: [],
              }),
        ),
      ),
    );

    render(<SystemStatus />);

    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(screen.getByText(/v0\.1\.0/)).toBeInTheDocument();
    expect(screen.getByText("Not downloaded")).toBeInTheDocument();
  });

  it("reports the API as offline when it cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );

    render(<SystemStatus />);

    expect(await screen.findByText("Offline")).toBeInTheDocument();
  });
});
