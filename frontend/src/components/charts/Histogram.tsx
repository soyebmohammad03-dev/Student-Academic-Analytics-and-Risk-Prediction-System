"use client";

import { useRef } from "react";

import type { Histogram as HistogramData } from "@/lib/statistics";

import { ChartFrame, niceTicks, pointer } from "./ChartFrame";

const W = 560;
const H = 220;
const M = { top: 8, right: 8, bottom: 30, left: 34 };

export function Histogram({
  data,
  subtitle,
  highlightBelow,
}: {
  data: HistogramData;
  subtitle?: string;
  /** Bins whose end is below this value are drawn in the second series colour. */
  highlightBelow?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const max = Math.max(...data.bins.map((b) => b.count), 1);
  const ticks = niceTicks(max);
  const top = ticks.at(-1) ?? max;
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const band = innerW / data.bins.length;
  const gap = Math.min(2, band * 0.2);
  const labelEvery = Math.ceil(data.bins.length / 11);

  return (
    <ChartFrame
      title={data.label}
      subtitle={subtitle ?? `n = ${data.n}`}
      table={{
        headers: ["Value", "Students", "Share"],
        rows: data.bins.map((b) => [b.label, b.count, `${((100 * b.count) / data.n).toFixed(1)}%`]),
      }}
    >
      {(setTooltip) => (
        <div ref={ref}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            role="img"
            aria-label={`Histogram of ${data.label}`}
          >
            {ticks.map((t) => {
              const y = M.top + innerH - (t / top) * innerH;
              return (
                <g key={t}>
                  <line x1={M.left} x2={W - M.right} y1={y} y2={y} className="stroke-separator" />
                  <text
                    x={M.left - 6}
                    y={y}
                    dy="0.32em"
                    textAnchor="end"
                    className="fill-text-tertiary text-[10px] tabular-nums"
                  >
                    {t}
                  </text>
                </g>
              );
            })}
            {data.bins.map((b, i) => {
              const h = (b.count / top) * innerH;
              const x = M.left + i * band + gap / 2;
              const below = highlightBelow !== undefined && b.end < highlightBelow;
              return (
                <g key={b.label}>
                  <rect
                    x={x}
                    y={M.top + innerH - h}
                    width={Math.max(band - gap, 1)}
                    height={h}
                    rx={Math.min(3, (band - gap) / 3)}
                    fill={below ? "var(--chart-2)" : "var(--chart-1)"}
                  />
                  <rect
                    x={M.left + i * band}
                    y={M.top}
                    width={band}
                    height={innerH}
                    fill="transparent"
                    onMouseMove={(e) =>
                      setTooltip({
                        ...pointer(e, ref.current),
                        content: (
                          <>
                            <span className="font-medium">{b.label}</span>: {b.count} students (
                            {((100 * b.count) / data.n).toFixed(1)}%)
                          </>
                        ),
                      })
                    }
                  />
                  {i % labelEvery === 0 && (
                    <text
                      x={M.left + i * band + band / 2}
                      y={H - M.bottom + 16}
                      textAnchor="middle"
                      className="fill-text-tertiary text-[10px] tabular-nums"
                    >
                      {b.label}
                    </text>
                  )}
                </g>
              );
            })}
            <line
              x1={M.left}
              x2={W - M.right}
              y1={M.top + innerH}
              y2={M.top + innerH}
              className="stroke-text-tertiary"
            />
          </svg>
          {highlightBelow !== undefined && (
            <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-secondary">
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm" style={{ background: "var(--chart-2)" }} />
                Below {highlightBelow} (academic risk)
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm" style={{ background: "var(--chart-1)" }} />
                {highlightBelow} or above
              </span>
            </p>
          )}
        </div>
      )}
    </ChartFrame>
  );
}
