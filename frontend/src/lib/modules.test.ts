import { describe, expect, it } from "vitest";

import { allModules, getModule } from "./modules";

describe("module registry", () => {
  it("has unique keys and routes", () => {
    expect(new Set(allModules.map((m) => m.key)).size).toBe(allModules.length);
    expect(new Set(allModules.map((m) => m.href)).size).toBe(allModules.length);
  });

  it("marks only delivered modules as available", () => {
    const available = allModules.filter((m) => m.status === "available").map((m) => m.key);
    expect(available).toEqual(["data", "statistics", "eda"]);
  });

  it("documents the scope of every module", () => {
    for (const m of allModules) expect(m.scope.length).toBeGreaterThan(0);
  });

  it("throws for unknown modules", () => {
    expect(() => getModule("nope")).toThrow();
  });
});
