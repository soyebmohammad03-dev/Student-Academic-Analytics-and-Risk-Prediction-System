import axe from "axe-core";
import { expect } from "vitest";

/**
 * Run axe-core on a rendered container. Colour contrast needs real layout, so it is
 * checked in the browser instead (see docs/ACCESSIBILITY.md). Collapsed
 * <details> are opened first so hidden tables are checked too.
 */
export async function expectNoAxeViolations(container: Element) {
  // Check collapsed content too (e.g. every chart's "Show data" table).
  container.querySelectorAll("details").forEach((d) => (d.open = true));
  const result = await axe.run(container, {
    rules: { "color-contrast": { enabled: false }, region: { enabled: false } },
  });
  const summary = result.violations.map(
    (v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(", ")})`,
  );
  expect(summary).toEqual([]);
}
