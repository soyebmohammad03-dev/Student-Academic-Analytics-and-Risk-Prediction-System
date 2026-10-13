import { ChartFrame } from "@/components/charts/ChartFrame";
import { KindBadge } from "@/components/ui/Callout";
import type { ScenarioSensitivity, Sensitivity } from "@/lib/risk";
import { scenarioInfo } from "@/lib/models";

function outputLabel(task: string, value: number, grade: number | null) {
  return task === "regression" && grade !== null ? grade.toFixed(1) : value.toFixed(3);
}

/**
 * Fixed output scale, so tiny differences are never stretched across the chart:
 * grades 0–20, probabilities 0–1, decision scores at least 2 units around 0.
 */
export function outputDomain(data: Sensitivity): [number, number] {
  if (data.task === "regression") return [0, 20];
  if (/probability/i.test(data.output)) return [0, 1];
  const outputs = data.points.map((p) => p.output);
  const lo = Math.min(...outputs, 0);
  const hi = Math.max(...outputs, 0);
  const span = Math.max(hi - lo, 2);
  const mid = (lo + hi) / 2;
  return [mid - span / 2, mid + span / 2];
}

/** Model output for each value of one attribute, everything else held as entered. */
export function SensitivityChart({ data }: { data: Sensitivity }) {
  const [lo, hi] = outputDomain(data);
  const pos = (v: number) => `${(100 * (Math.min(Math.max(v, lo), hi) - lo)) / (hi - lo)}%`;

  return (
    <ChartFrame
      title={`${data.label}: model response`}
      subtitle={data.output}
      table={{
        headers: ["Value", "Model output", "Flag", "Training students", "Current"],
        rows: data.points.map((p) => [
          p.label,
          outputLabel(data.task, p.output, p.predicted_grade),
          p.at_risk === null ? "—" : p.at_risk ? "at risk" : "not at risk",
          `${p.support}${p.sparse ? " (sparse)" : ""}`,
          p.current ? "yes" : "",
        ]),
      }}
    >
      {() => (
        <div>
          <div className="mb-3">
            <KindBadge kind="sensitivity" />
          </div>
          <ul className="space-y-2" aria-label={`Model output by ${data.label}`}>
            {data.points.map((p) => (
              <li
                key={p.value}
                className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_3.5rem] items-center gap-3 text-[12px] sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_4rem]"
              >
                <span
                  className={
                    p.current ? "truncate font-medium text-text" : "truncate text-text-secondary"
                  }
                  title={p.label}
                >
                  {p.label}
                  {p.current && <span className="text-accent"> · entered</span>}
                </span>
                <span className="relative h-4">
                  <span className="absolute inset-x-0 top-1/2 h-px bg-separator" aria-hidden />
                  <span
                    className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                    style={{
                      left: pos(p.output),
                      background: p.sparse ? "var(--text-tertiary)" : "var(--chart-1)",
                      outline: p.current ? "2px solid var(--accent)" : undefined,
                      outlineOffset: 2,
                    }}
                    title={`${outputLabel(data.task, p.output, p.predicted_grade)} · ${p.support} training students`}
                  />
                </span>
                <span className="text-right text-text tabular-nums">
                  {outputLabel(data.task, p.output, p.predicted_grade)}
                  {p.sparse && <span className="block text-[10px] text-caution">sparse</span>}
                </span>
              </li>
            ))}
          </ul>
          <div
            className="mt-1 grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_3.5rem] gap-3 text-[10px] text-text-tertiary tabular-nums sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_4rem]"
            aria-hidden
          >
            <span />
            <span className="flex justify-between">
              <span>{lo.toFixed(data.task === "regression" ? 0 : 1)}</span>
              <span>{hi.toFixed(data.task === "regression" ? 0 : 1)}</span>
            </span>
          </div>
          <p className="mt-3 text-[12px] leading-[18px] text-text-secondary">{data.note}</p>
        </div>
      )}
    </ChartFrame>
  );
}

/** The same record under each scenario its grades allow; each has its own model. */
export function ScenarioSensitivityCard({ data }: { data: ScenarioSensitivity }) {
  return (
    <ChartFrame
      title="Same record, different scenarios"
      subtitle="Each scenario uses its own selected model and only the information it allows."
    >
      {() => (
        <div>
          <div className="mb-3">
            <KindBadge kind="sensitivity" />
          </div>
          <ul className="divide-y divide-separator text-[13px]">
            {data.items.map((item) => (
              <li key={item.scenario} className="flex items-baseline justify-between gap-3 py-2">
                <span className="min-w-0">
                  <span className="font-medium text-text">{scenarioInfo[item.scenario].label}</span>
                  <span className="block truncate text-[12px] text-text-tertiary">
                    {item.model_label}
                  </span>
                </span>
                <span className="shrink-0 text-right text-text tabular-nums">
                  {data.task === "regression"
                    ? `${item.predicted_grade?.toFixed(1)} / 20`
                    : item.at_risk
                      ? "Flagged"
                      : "Not flagged"}
                  {data.task === "classification" && (
                    <span className="block text-[11px] text-text-tertiary">
                      score {item.output.toFixed(3)}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
          {data.skipped.length > 0 && (
            <p className="mt-2 text-[12px] text-text-tertiary">
              Not shown: {data.skipped.map((s) => scenarioInfo[s].label).join(", ")} (the grades it
              needs were not provided).
            </p>
          )}
          <p className="mt-3 text-[12px] leading-[18px] text-text-secondary">{data.note}</p>
        </div>
      )}
    </ChartFrame>
  );
}
