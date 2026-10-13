"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useSyncExternalStore } from "react";

import type { Cohort } from "./api";
import type { Scenario } from "./risk";

/*
 * Cohort and scenario are shared across pages so that switching pages keeps the
 * analysis context. The URL (?cohort=, ?scenario=) wins, which keeps links shareable;
 * otherwise the last choice in this tab (sessionStorage) is used. Only these two short
 * strings are stored; student records never are.
 */

export const cohortOptions = [
  { value: "math", label: "Mathematics" },
  { value: "portuguese", label: "Portuguese" },
] as const satisfies ReadonlyArray<{ value: Cohort; label: string }>;

export function parseCohort(value: string | null): Cohort {
  return value === "portuguese" ? "portuguese" : "math";
}

export function parseScenario(value: string | null): Scenario {
  return value === "mid_year" || value === "full_history" ? value : "early";
}

const STORAGE_PREFIX = "saarps.";
const CHANGE_EVENT = "saarps:selection";

function readStored(name: string): string | null {
  try {
    return sessionStorage.getItem(STORAGE_PREFIX + name);
  } catch {
    return null;
  }
}

function writeStored(name: string, value: string) {
  try {
    sessionStorage.setItem(STORAGE_PREFIX + name, value);
  } catch {
    // Storage unavailable: the URL still carries the selection.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function subscribe(onChange: () => void) {
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => window.removeEventListener(CHANGE_EVENT, onChange);
}

function useSharedParam<T extends string>(
  name: string,
  parse: (value: string | null) => T,
): [T, (next: T) => void] {
  const searchParams = useSearchParams();
  const fromUrl = searchParams.get(name);
  const stored = useSyncExternalStore(
    subscribe,
    () => readStored(name),
    () => null,
  );
  const value = parse(fromUrl ?? stored);

  // A shared link sets the context for the following pages too.
  useEffect(() => {
    if (fromUrl !== null && parse(fromUrl) !== parse(readStored(name))) {
      writeStored(name, parse(fromUrl));
    }
  }, [fromUrl, name, parse]);

  const select = useCallback(
    (next: T) => {
      const params = new URLSearchParams(window.location.search);
      params.set(name, next);
      window.history.replaceState(null, "", `?${params}`);
      writeStored(name, next);
    },
    [name],
  );
  return [value, select];
}

/** Selected cohort, shared across pages. */
export function useCohort(): [Cohort, (next: Cohort) => void] {
  return useSharedParam("cohort", parseCohort);
}

/** Selected input scenario, shared across pages that use one. */
export function useScenario(): [Scenario, (next: Scenario) => void] {
  return useSharedParam("scenario", parseScenario);
}
