"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";

export interface TooltipState {
  x: number;
  y: number;
  content: React.ReactNode;
}

/**
 * Figure wrapper shared by every chart: title, optional subtitle, a hover tooltip
 * layer, and a "Show data" table so values never depend on reading colour or shape.
 */
export function ChartFrame({
  title,
  subtitle,
  table,
  className,
  children,
}: {
  title: string;
  subtitle?: string;
  table?: { headers: string[]; rows: Array<Array<string | number>> };
  className?: string;
  children: (setTooltip: (t: TooltipState | null) => void) => React.ReactNode;
}) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  return (
    <figure className={cn("min-w-0 rounded-2xl bg-surface p-4 shadow-card sm:p-5", className)}>
      <figcaption className="mb-3">
        <p className="text-[14px] font-semibold text-text">{title}</p>
        {subtitle && <p className="mt-0.5 text-[12px] text-text-secondary">{subtitle}</p>}
      </figcaption>
      <div className="relative" onMouseLeave={() => setTooltip(null)}>
        {children(setTooltip)}
        {tooltip && (
          <div
            role="status"
            className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-surface px-2.5 py-1.5 text-[12px] whitespace-nowrap text-text shadow-raised"
            style={{ left: tooltip.x, top: tooltip.y - 8 }}
          >
            {tooltip.content}
          </div>
        )}
      </div>
      {table && (
        <details className="mt-3 text-[12px]">
          <summary className="cursor-pointer text-text-secondary select-none hover:text-text">
            Show data
          </summary>
          <div
            tabIndex={0}
            role="region"
            aria-label={`${title}: data table`}
            className="mt-2 max-h-64 overflow-auto rounded-lg border border-separator"
          >
            <table className="w-full text-left tabular-nums">
              <thead className="sticky top-0 bg-surface-muted text-text-tertiary">
                <tr>
                  {table.headers.map((h) => (
                    <th key={h} scope="col" className="px-3 py-1.5 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-separator text-text">
                {table.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((cell, j) => (
                      <td key={j} className="px-3 py-1.5">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </figure>
  );
}

/** Pointer position relative to the chart container, for tooltips. */
export function pointer(event: React.MouseEvent, container: HTMLElement | null) {
  const rect = container?.getBoundingClientRect();
  return rect ? { x: event.clientX - rect.left, y: event.clientY - rect.top } : { x: 0, y: 0 };
}

/** "Nice" upper bound and ticks for a count axis. */
export function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0];
  const raw = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? raw;
  const ticks = [];
  for (let t = 0; t <= max + step * 0.999; t += step) ticks.push(Math.round(t * 1000) / 1000);
  return ticks;
}
