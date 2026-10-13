"use client";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { fmt } from "@/lib/format";
import { type ScenarioComparison, metricInfo } from "@/lib/models";

/**
 * Selected model per scenario: cross-validated mean ± SD (dot and whisker), the
 * held-out test score (ring) and the baseline's CV score (grey tick), on one axis.
 */
export function ScenarioChart({ data }: { data: ScenarioComparison }) {
  const metric = data.primary_metric;
  const info = metricInfo[metric];
  const values = data.rows.flatMap((r) => [
    (r.cv[metric] ?? 0) + (r.cv_std[metric] ?? 0),
    r.test[metric] ?? 0,
    r.baseline_cv[metric] ?? 0,
  ]);
  const bounded = metric === "f1" || metric === "roc_auc" || metric === "recall";
  const max = bounded ? 1 : Math.ceil(Math.max(...values, 1));
  const x = (v: number | null) => `${(100 * Math.max(0, v ?? 0)) / max}%`;
  const ticks = bounded ? [0, 0.25, 0.5, 0.75, 1] : Array.from({ length: max + 1 }, (_, i) => i);

  return (
    <ChartFrame
      title={`${info?.label ?? metric} by scenario`}
      subtitle={`${info?.higherIsBetter ? "Higher" : "Lower"} is better. Each scenario has its own selected model.`}
      table={{
        headers: ["Scenario", "Selected model", "CV mean", "CV SD", "Test", "Baseline CV"],
        rows: data.rows.map((r) => [
          r.label,
          r.selected_label,
          fmt(r.cv[metric], 3),
          fmt(r.cv_std[metric], 3),
          fmt(r.test[metric], 3),
          fmt(r.baseline_cv[metric], 3),
        ]),
      }}
    >
      {() => (
        <div>
          <ul className="space-y-4" aria-label={`${info?.short ?? metric} by scenario`}>
            {data.rows.map((r) => {
              const mean = r.cv[metric];
              const sd = r.cv_std[metric] ?? 0;
              return (
                <li
                  key={r.scenario}
                  className="grid grid-cols-1 gap-1.5 sm:grid-cols-[minmax(0,10rem)_minmax(0,1fr)] sm:items-center sm:gap-4"
                >
                  <div className="min-w-0 text-[12px]">
                    <p className="font-medium text-text">{r.label}</p>
                    <p className="truncate text-text-tertiary" title={r.selected_label}>
                      {r.selected_label}
                    </p>
                  </div>
                  <div className="relative h-7">
                    <span className="absolute inset-x-0 top-1/2 h-px bg-separator" aria-hidden />
                    {mean !== null && (
                      <span
                        className="absolute top-1/2 h-[2px] -translate-y-1/2 rounded bg-chart-1/40"
                        style={{
                          left: x(mean - sd),
                          width: `calc(${x(mean + sd)} - ${x(mean - sd)})`,
                        }}
                        aria-hidden
                      />
                    )}
                    <span
                      className="absolute top-1/2 h-4 w-[2px] -translate-x-1/2 -translate-y-1/2 rounded bg-text-tertiary"
                      style={{ left: x(r.baseline_cv[metric]) }}
                      title={`Baseline CV ${fmt(r.baseline_cv[metric], 3)}`}
                    />
                    {mean !== null && (
                      <span
                        className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-chart-1"
                        style={{ left: x(mean) }}
                        title={`CV ${fmt(mean, 3)} ± ${fmt(sd, 3)}`}
                      />
                    )}
                    {r.test[metric] !== null && (
                      <span
                        className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-chart-2 bg-surface"
                        style={{ left: x(r.test[metric]) }}
                        title={`Test ${fmt(r.test[metric], 3)}`}
                      />
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="mt-2 sm:ml-[calc(10rem+1rem)]">
            <div className="relative h-4 text-[10px] text-text-tertiary tabular-nums" aria-hidden>
              {ticks.map((t) => (
                <span key={t} className="absolute -translate-x-1/2" style={{ left: x(t) }}>
                  {t}
                </span>
              ))}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-secondary">
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full bg-chart-1" aria-hidden /> CV mean (± 1 SD)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full border-2 border-chart-2" aria-hidden />{" "}
              Held-out test
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-3 w-[2px] rounded bg-text-tertiary" aria-hidden /> Baseline (CV)
            </span>
          </div>
        </div>
      )}
    </ChartFrame>
  );
}
