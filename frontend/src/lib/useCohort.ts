"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import type { Cohort } from "./api";

export const cohortOptions = [
  { value: "math", label: "Mathematics" },
  { value: "portuguese", label: "Portuguese" },
] as const satisfies ReadonlyArray<{ value: Cohort; label: string }>;

export function parseCohort(value: string | null): Cohort {
  return value === "portuguese" ? "portuguese" : "math";
}

/** Selected cohort, initialised from and written back to `?cohort=` (shareable URLs). */
export function useCohort(): [Cohort, (next: Cohort) => void] {
  const searchParams = useSearchParams();
  const [cohort, setCohort] = useState<Cohort>(() => parseCohort(searchParams.get("cohort")));
  function select(next: Cohort) {
    setCohort(next);
    window.history.replaceState(null, "", `?cohort=${next}`);
  }
  return [cohort, select];
}
