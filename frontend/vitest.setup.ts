import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // The shared cohort/scenario selection lives in the URL and sessionStorage.
  sessionStorage.clear();
  window.history.replaceState(null, "", "/");
});
