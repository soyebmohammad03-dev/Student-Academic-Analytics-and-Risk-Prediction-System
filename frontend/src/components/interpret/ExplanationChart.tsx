"use client";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { KindBadge } from "@/components/ui/Callout";
import type { Explanation } from "@/lib/risk";

const digits = (scale: number) => (scale < 1 ? 3 : 2);

/**
 * Additive explanation of one model output: each attribute's Shapley contribution as a
 * diverging bar from zero, with ±2 standard errors, from the base value to the output.
 */
export function ExplanationChart({
  explanation,
  title,
}: {
  explanation: Explanation;
  title: string;
}) {
  const rows = explanation.contributions;
  const span = Math.max(
    ...rows.map((r) => Math.abs(r.contribution) + 2 * r.standard_error),
    Math.abs(explanation.other_contribution),
    1e-9,
  );
  const d = digits(Math.abs(explanation.prediction));
  const pos = (v: number) => 50 + (50 * v) / span;

  return (
    <ChartFrame
      title={title}
      subtitle={`${explanation.output}. Base value ${explanation.base_value.toFixed(d)} → this record ${explanation.prediction.toFixed(d)}.`}
      table={{
        headers: ["Attribute", "Value", "Contribution", "± SE", "Direction"],
        rows: [
          ...rows.map((r) => [
            r.label,
            r.value,
            r.contribution.toFixed(d + 1),
            r.standard_error.toFixed(d + 1),
            r.direction,
          ]),
          [
            `${explanation.other_attributes} other attributes`,
            "",
            explanation.other_contribution.toFixed(d + 1),
            "",
            "",
          ],
        ],
      }}
    >
      {() => (
        <div>
          <div className="mb-3">
            <KindBadge kind="explanation" />
          </div>
          <ul className="space-y-2" aria-label={`${title}: contributions`}>
            {rows.map((r) => {
              const start = Math.min(pos(0), pos(r.contribution));
              const width = Math.abs(pos(r.contribution) - pos(0));
              const negligible = r.direction === "negligible";
              return (
                <li
                  key={r.attribute}
                  className="grid grid-cols-[minmax(0,9.5rem)_minmax(0,1fr)_4.25rem] items-center gap-3 text-[12px] sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_4.5rem]"
                >
                  <span
                    className="min-w-0 truncate text-text-secondary"
                    title={`${r.label} = ${r.value}`}
                  >
                    {r.label}
                    <span className="text-text-tertiary"> = {r.value}</span>
                  </span>
                  <span
                    className="relative h-4"
                    title={`${r.direction}, ${r.contribution.toFixed(d + 1)} ± ${r.standard_error.toFixed(d + 1)}`}
                  >
                    <span className="absolute inset-y-0 left-1/2 w-px bg-separator" aria-hidden />
                    <span
                      className="absolute top-0.5 bottom-0.5 rounded-[3px]"
                      style={{
                        left: `${start}%`,
                        width: `${width}%`,
                        background: negligible
                          ? "var(--fill-strong)"
                          : r.contribution > 0
                            ? "var(--chart-2)"
                            : "var(--chart-1)",
                      }}
                    />
                    <span
                      className="absolute top-1/2 h-px -translate-y-1/2 bg-text-secondary"
                      style={{
                        left: `${pos(r.contribution - 2 * r.standard_error)}%`,
                        width: `${pos(r.contribution + 2 * r.standard_error) - pos(r.contribution - 2 * r.standard_error)}%`,
                      }}
                      aria-hidden
                    />
                  </span>
                  <span className="text-right text-text tabular-nums">
                    {r.contribution > 0 ? "+" : ""}
                    {r.contribution.toFixed(d)}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-[12px] text-text-secondary tabular-nums">
            {explanation.other_attributes} other attributes together:{" "}
            {explanation.other_contribution > 0 ? "+" : ""}
            {explanation.other_contribution.toFixed(d)}
          </p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-secondary">
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-[3px] bg-chart-2" aria-hidden /> Raises the output
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-[3px] bg-chart-1" aria-hidden /> Lowers the output
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-[3px] bg-fill-strong" aria-hidden /> Negligible
              (within 2 SE of 0)
            </span>
          </div>
          <p className="mt-3 text-[12px] leading-[18px] text-text-secondary">
            {explanation.reading}
          </p>
          <details className="mt-2 text-[12px] text-text-secondary">
            <summary className="cursor-pointer select-none hover:text-text">
              Method and limitations
            </summary>
            <p className="mt-2 leading-[18px]">
              {explanation.method} Background: {explanation.background}; {explanation.n_samples}{" "}
              samples, seed {explanation.seed}.
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-4 leading-[18px]">
              {explanation.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </ChartFrame>
  );
}
