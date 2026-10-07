import type { Num } from "./statistics";

/** Number with fixed decimals, or an em dash when undefined. */
export function fmt(value: Num | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

/** p-value in APA style: "< .001" or ".034". */
export function fmtP(p: Num | undefined): string {
  if (p === null || p === undefined) return "—";
  if (p < 0.001) return "< .001";
  return p.toFixed(3).replace(/^0/, "");
}

export function fmtPercent(value: Num | undefined, digits = 1): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(digits)}%`;
}
