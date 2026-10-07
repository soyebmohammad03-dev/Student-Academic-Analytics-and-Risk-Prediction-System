"use client";

import { useRef } from "react";

import { fmt } from "@/lib/format";
import type { BoxPlotData } from "@/lib/statistics";

import { ChartFrame, pointer } from "./ChartFrame";

const W = 480;
const ROW = 34;
const M = { top: 6, right: 12, bottom: 28, left: 156 };
const SCALE_MAX = 20;

/** Horizontal box plots of G3 (0–20) per group: whiskers at 1.5·IQR, mean as a dot. */
export function BoxPlot({ data, subtitle }: { data: BoxPlotData; subtitle?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const H = M.top + data.groups.length * ROW + M.bottom;
  const innerW = W - M.left - M.right;
  const x = (v: number | null) => M.left + ((v ?? 0) / SCALE_MAX) * innerW;

  return (
    <ChartFrame
      title={`${data.outcome} by ${data.variable_label.toLowerCase()}`}
      subtitle={subtitle ?? "Box: quartiles · line: median · dot: mean · whiskers: 1.5 × IQR"}
      table={{
        headers: ["Group", "n", "Median", "Q1–Q3", "Mean", "Whiskers"],
        rows: data.groups.map((g) => [
          g.label, g.n, fmt(g.median, 1), `${fmt(g.q1, 1)}–${fmt(g.q3, 1)}`, fmt(g.mean, 2),
          `${fmt(g.whisker_low, 0)}–${fmt(g.whisker_high, 0)}`,
        ]), // prettier-ignore
      }}
    >
      {(setTooltip) => (
        <div ref={ref}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            role="img"
            aria-label={`Box plots of ${data.outcome} by ${data.variable_label}`}
          >
            {[0, 5, 10, 15, 20].map((t) => (
              <g key={t}>
                <line
                  x1={x(t)}
                  x2={x(t)}
                  y1={M.top}
                  y2={H - M.bottom}
                  className="stroke-separator"
                />
                <text
                  x={x(t)}
                  y={H - M.bottom + 16}
                  textAnchor="middle"
                  className="fill-text-tertiary text-[10px]"
                >
                  {t}
                </text>
              </g>
            ))}
            {data.groups.map((g, i) => {
              const cy = M.top + i * ROW + ROW / 2;
              return (
                <g
                  key={g.key}
                  onMouseMove={(e) =>
                    setTooltip({
                      ...pointer(e, ref.current),
                      content: (
                        <>
                          <span className="font-medium">{g.label}</span> · n = {g.n} · median{" "}
                          {fmt(g.median, 1)} · mean {fmt(g.mean, 2)}
                        </>
                      ),
                    })
                  }
                >
                  <rect
                    x={M.left}
                    y={cy - ROW / 2}
                    width={innerW}
                    height={ROW}
                    fill="transparent"
                  />
                  <text
                    x={M.left - 10}
                    y={cy}
                    dy="0.32em"
                    textAnchor="end"
                    className="fill-text-secondary text-[11px]"
                  >
                    {g.label.length > 22 ? `${g.label.slice(0, 21)}…` : g.label}
                    <tspan className="fill-text-tertiary"> ({g.n})</tspan>
                  </text>
                  <line
                    x1={x(g.whisker_low)}
                    x2={x(g.whisker_high)}
                    y1={cy}
                    y2={cy}
                    className="stroke-text-tertiary"
                    strokeWidth={1.5}
                  />
                  <rect
                    x={x(g.q1)}
                    y={cy - 9}
                    width={Math.max(x(g.q3) - x(g.q1), 2)}
                    height={18}
                    rx={4}
                    fill="var(--chart-1)"
                    fillOpacity={0.25}
                    stroke="var(--chart-1)"
                    strokeWidth={1.5}
                  />
                  <line
                    x1={x(g.median)}
                    x2={x(g.median)}
                    y1={cy - 9}
                    y2={cy + 9}
                    stroke="var(--chart-1)"
                    strokeWidth={2.5}
                  />
                  <circle
                    cx={x(g.mean)}
                    cy={cy}
                    r={3}
                    className="fill-surface"
                    stroke="var(--chart-1)"
                    strokeWidth={1.5}
                  />
                  {g.outliers.map((o) => (
                    <circle
                      key={o.value}
                      cx={x(o.value)}
                      cy={cy}
                      r={2.5}
                      className="fill-text-tertiary"
                    />
                  ))}
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </ChartFrame>
  );
}
