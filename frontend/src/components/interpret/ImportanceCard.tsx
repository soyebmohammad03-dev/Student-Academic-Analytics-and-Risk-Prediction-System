import { ChartFrame } from "@/components/charts/ChartFrame";
import { fmt } from "@/lib/format";
import type { ImportanceResult } from "@/lib/risk";

const TOP = 8;

/** One importance method on its own scale; methods are never placed on a shared axis. */
export function ImportanceCard({ result }: { result: ImportanceResult }) {
  const items = result.items.filter((i) => i.value !== 0).slice(0, TOP);
  const max = Math.max(...items.map((i) => Math.abs(i.value)), 1e-9);
  const signed = result.method === "standardised_coefficient";
  return (
    <ChartFrame
      title={result.method_label}
      subtitle={`${result.unit}. ${result.data}`}
      table={{
        headers: ["Rank", "Feature", "Value", "SD"],
        rows: items.map((i) => [i.rank, i.label, i.value.toFixed(3), fmt(i.std, 3)]),
      }}
    >
      {() => (
        <>
          {items.length === 0 ? (
            <p className="text-[13px] text-text-secondary">
              No attribute has a non-zero value for this method.
            </p>
          ) : (
            <ul className="space-y-2" aria-label={result.method_label}>
              {items.map((i) => (
                <li
                  key={i.feature}
                  className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_auto] items-center gap-3 text-[12px] sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)_auto]"
                >
                  <span className="truncate text-text-secondary" title={i.label}>
                    {i.label}
                  </span>
                  <span className="h-3 rounded-r bg-fill">
                    <span
                      className="block h-full rounded-r"
                      style={{
                        width: `${(100 * Math.abs(i.value)) / max}%`,
                        // Coefficients: sign shown by colour. Other methods: a negative
                        // value means no measurable reliance, so it is drawn muted.
                        background:
                          i.value >= 0
                            ? "var(--chart-1)"
                            : signed
                              ? "var(--chart-2)"
                              : "var(--text-tertiary)",
                      }}
                    />
                  </span>
                  <span className="text-right text-text tabular-nums">
                    {signed && i.value > 0 ? "+" : ""}
                    {i.value.toFixed(3)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <ul className="mt-3 list-disc space-y-1 pl-4 text-[11px] leading-4 text-text-tertiary">
            {result.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </>
      )}
    </ChartFrame>
  );
}
