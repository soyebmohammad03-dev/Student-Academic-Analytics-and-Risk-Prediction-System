"use client";

import { useRef } from "react";

import { fmt } from "@/lib/format";
import type { ScatterData } from "@/lib/statistics";

import { ChartFrame, niceTicks, pointer } from "./ChartFrame";

const W = 360;
const H = 300;
const M = { top: 8, right: 10, bottom: 36, left: 36 };

/** Scatter of integer-valued variables; identical points are aggregated and sized by count. */
export function Scatter({ data }: { data: ScatterData }) {
  const ref = useRef<HTMLDivElement>(null);
  const xMax = Math.max(...data.points.map((p) => p.x), 1);
  const xTicks = niceTicks(xMax);
  const xTop = xTicks.at(-1) ?? xMax;
  const yTicks = [0, 5, 10, 15, 20];
  const maxCount = Math.max(...data.points.map((p) => p.count), 1);
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const sx = (v: number) => M.left + (v / xTop) * innerW;
  const sy = (v: number) => M.top + innerH - (v / 20) * innerH;

  return (
    <ChartFrame
      title={`${data.y_label} vs ${data.x_label.toLowerCase()}`}
      subtitle={`n = ${data.n} · Spearman ρ = ${fmt(data.spearman_r)} · larger dots = more students`}
      table={{
        headers: [data.x, data.y, "Students"],
        rows: data.points.map((p) => [p.x, p.y, p.count]),
      }}
    >
      {(setTooltip) => (
        <div ref={ref}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            role="img"
            aria-label={`Scatter plot of ${data.y_label} against ${data.x_label}`}
          >
            {yTicks.map((t) => (
              <g key={`y${t}`}>
                <line
                  x1={M.left}
                  x2={W - M.right}
                  y1={sy(t)}
                  y2={sy(t)}
                  className="stroke-separator"
                />
                <text
                  x={M.left - 6}
                  y={sy(t)}
                  dy="0.32em"
                  textAnchor="end"
                  className="fill-text-tertiary text-[10px]"
                >
                  {t}
                </text>
              </g>
            ))}
            {xTicks.map((t) => (
              <text
                key={`x${t}`}
                x={sx(t)}
                y={H - M.bottom + 14}
                textAnchor="middle"
                className="fill-text-tertiary text-[10px]"
              >
                {t}
              </text>
            ))}
            <text
              x={M.left + innerW / 2}
              y={H - 4}
              textAnchor="middle"
              className="fill-text-secondary text-[10px]"
            >
              {data.x_label}
            </text>
            {data.points.map((p) => (
              <circle
                key={`${p.x}-${p.y}`}
                cx={sx(p.x)}
                cy={sy(p.y)}
                r={2.5 + 5.5 * Math.sqrt(p.count / maxCount)}
                fill="var(--chart-1)"
                fillOpacity={0.55}
                className="stroke-surface"
                strokeWidth={1}
                onMouseMove={(e) =>
                  setTooltip({
                    ...pointer(e, ref.current),
                    content: `${data.x} = ${p.x}, ${data.y} = ${p.y}: ${p.count} student${p.count === 1 ? "" : "s"}`,
                  })
                }
              />
            ))}
          </svg>
        </div>
      )}
    </ChartFrame>
  );
}
