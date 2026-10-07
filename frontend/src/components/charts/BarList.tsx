import type { BarChartData } from "@/lib/statistics";

import { ChartFrame } from "./ChartFrame";

/** Horizontal bars with direct labels (count and share), for categorical distributions. */
export function BarList({ data }: { data: BarChartData }) {
  const max = Math.max(...data.bars.map((b) => b.count), 1);
  return (
    <ChartFrame
      title={data.label}
      subtitle={`n = ${data.n}`}
      table={{
        headers: ["Category", "Students", "Share"],
        rows: data.bars.map((b) => [b.label, b.count, `${b.percent.toFixed(1)}%`]),
      }}
    >
      {() => (
        <ul className="space-y-2" aria-label={`Distribution of ${data.label}`}>
          {data.bars.map((b) => (
            <li
              key={b.key}
              className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 text-[12px]"
            >
              <span className="truncate text-text-secondary" title={b.label}>
                {b.label}
              </span>
              <span className="h-3 rounded-r bg-fill">
                <span
                  className="block h-full rounded-r"
                  style={{ width: `${(100 * b.count) / max}%`, background: "var(--chart-1)" }}
                />
              </span>
              <span className="text-right text-text tabular-nums">
                {b.count} <span className="text-text-tertiary">({b.percent.toFixed(0)}%)</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </ChartFrame>
  );
}
