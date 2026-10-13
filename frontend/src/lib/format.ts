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

/** A 0–1 proportion as a percentage. */
export function fmtShare(value: Num | undefined, digits = 0): string {
  return value === null || value === undefined ? "—" : `${(100 * value).toFixed(digits)}%`;
}

/** 95% interval of proportions, e.g. "28–38%". */
export function fmtInterval(ci: { low: Num; high: Num } | null | undefined, digits = 0): string {
  if (!ci || ci.low === null || ci.high === null) return "—";
  return `${(100 * ci.low).toFixed(digits)}–${(100 * ci.high).toFixed(digits)}%`;
}

/** ISO timestamp as a readable date, independent of the viewer's locale. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
