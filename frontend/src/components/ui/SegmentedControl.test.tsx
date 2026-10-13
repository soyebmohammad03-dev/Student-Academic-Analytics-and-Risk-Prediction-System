import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { SegmentedControl } from "./SegmentedControl";

const options = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
] as const;

function Harness() {
  const [value, setValue] = useState<"a" | "b" | "c">("a");
  return <SegmentedControl label="Letters" options={options} value={value} onChange={setValue} />;
}

describe("SegmentedControl", () => {
  it("has one tab stop and moves the selection with arrow keys", () => {
    render(<Harness />);
    const alpha = screen.getByRole("radio", { name: "Alpha" });
    expect(alpha).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("radio", { name: "Beta" })).toHaveAttribute("tabindex", "-1");

    fireEvent.keyDown(alpha, { key: "ArrowRight" });
    const beta = screen.getByRole("radio", { name: "Beta" });
    expect(beta).toHaveAttribute("aria-checked", "true");
    expect(beta).toHaveFocus();

    fireEvent.keyDown(beta, { key: "ArrowLeft" });
    fireEvent.keyDown(screen.getByRole("radio", { name: "Alpha" }), { key: "ArrowLeft" });
    expect(screen.getByRole("radio", { name: "Gamma" })).toHaveAttribute("aria-checked", "true");
  });
});
