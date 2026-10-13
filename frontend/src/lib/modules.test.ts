import { describe, expect, it } from "vitest";

import { allModules } from "./modules";

describe("module registry", () => {
  it("has unique keys and routes", () => {
    expect(new Set(allModules.map((m) => m.key)).size).toBe(allModules.length);
    expect(new Set(allModules.map((m) => m.href)).size).toBe(allModules.length);
  });

  it("marks every delivered module as available", () => {
    const available = allModules.filter((m) => m.status === "available").map((m) => m.key);
    expect(available).toEqual([
      "data",
      "statistics",
      "eda",
      "models",
      "prediction",
      "interpretability",
      "risk",
    ]);
  });

  it("documents the scope of every module", () => {
    for (const m of allModules) expect(m.scope.length).toBeGreaterThan(0);
  });
});
