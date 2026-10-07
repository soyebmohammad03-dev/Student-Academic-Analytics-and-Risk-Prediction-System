import { describe, expect, it } from "vitest";

import { allModules, getModule } from "./modules";

describe("module registry", () => {
  it("has unique keys and routes", () => {
    expect(new Set(allModules.map((m) => m.key)).size).toBe(allModules.length);
    expect(new Set(allModules.map((m) => m.href)).size).toBe(allModules.length);
  });

  it("does not mark any module as available before it is built", () => {
    expect(allModules.every((m) => m.status === "planned")).toBe(true);
  });

  it("documents planned scope for every module", () => {
    for (const m of allModules) expect(m.scope.length).toBeGreaterThan(0);
  });

  it("throws for unknown modules", () => {
    expect(() => getModule("nope")).toThrow();
  });
});
