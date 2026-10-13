import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { expectNoAxeViolations } from "@/test/axe";

import MethodologyPage from "./page";

describe("Methodology page", () => {
  it("covers the required topics without claiming dropout prediction", async () => {
    const { container } = render(<MethodologyPage />);
    for (const heading of [
      "Research basis",
      "Dataset",
      "Input scenarios",
      "Academic risk",
      "Target leakage prevention",
      "Limitations and responsible use",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    }
    expect(screen.getByText(/never claims to predict dropout/)).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });
});
