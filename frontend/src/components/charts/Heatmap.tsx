"use client";

import { useRef } from "react";

import { fmt, fmtP } from "@/lib/format";
import type { CorrelationMatrix } from "@/lib/statistics";

import { ChartFrame, pointer } from "./ChartFrame";

/** Diverging fill: blue for positive, red for negative, grey at zero. */
function cellColor(r: number | null): string {
  if (r === null) return "var(--fill)";
  const pct = Math.round(Math.min(Math.abs(r), 1) * 100);
  const pole = r >= 0 ? "var(--chart-positive)" : "var(--chart-negative)";
  return `color-mix(in oklab, ${pole} ${pct}%, var(--chart-neutral))`;
}

export function Heatmap({ data }: { data: CorrelationMatrix }) {
  const ref = useRef<HTMLDivElement>(null);
  const k = data.variables.length;
  const cell = 30;
  const left = 70;
  const topPad = 70;
  const size = left + k * cell;

  return (
    <ChartFrame
      title="Spearman correlation matrix"
      subtitle={`n = ${data.n} · blue = positive, red = negative · ✱ = BH-adjusted p < .05`}
      table={{
        headers: ["Variable", ...data.variables],
        rows: data.variables.map((v, i) => [v, ...data.r[i].map((r) => fmt(r))]),
      }}
    >
      {(setTooltip) => (
        <div
          ref={ref}
          tabIndex={0}
          role="region"
          aria-label="Correlation heatmap (scrollable)"
          className="overflow-x-auto"
        >
          <svg
            viewBox={`0 0 ${size} ${topPad + k * cell}`}
            className="h-auto w-full min-w-[520px]"
            role="img"
            aria-label="Correlation heatmap"
          >
            {data.variables.map((v, j) => (
              <text
                key={`c${v}`}
                transform={`translate(${left + j * cell + cell / 2}, ${topPad - 6}) rotate(-50)`}
                className="fill-text-secondary font-mono text-[10px]"
              >
                {v}
              </text>
            ))}
            {data.variables.map((row, i) => (
              <g key={row}>
                <text
                  x={left - 6}
                  y={topPad + i * cell + cell / 2}
                  dy="0.32em"
                  textAnchor="end"
                  className="fill-text-secondary font-mono text-[10px]"
                >
                  {row}
                </text>
                {data.variables.map((col, j) => {
                  const r = data.r[i][j];
                  const p = data.p_adjusted[i][j];
                  const strong = r !== null && Math.abs(r) >= 0.5;
                  return (
                    <g
                      key={col}
                      onMouseMove={(e) =>
                        setTooltip({
                          ...pointer(e, ref.current),
                          content: (
                            <>
                              <span className="font-medium">
                                {data.labels[i]} × {data.labels[j]}
                              </span>
                              : ρ = {fmt(r)}
                              {i !== j && <> · BH p {fmtP(p)}</>}
                            </>
                          ),
                        })
                      }
                    >
                      <rect
                        x={left + j * cell + 1}
                        y={topPad + i * cell + 1}
                        width={cell - 2}
                        height={cell - 2}
                        rx={4}
                        fill={cellColor(r)}
                      />
                      <text
                        x={left + j * cell + cell / 2}
                        y={topPad + i * cell + cell / 2}
                        dy="0.32em"
                        textAnchor="middle"
                        className={
                          strong
                            ? "fill-white text-[9px] tabular-nums"
                            : "fill-text text-[9px] tabular-nums"
                        }
                      >
                        {r === null
                          ? ""
                          : (Math.abs(r) < 0.005 ? 0 : r).toFixed(2).replace("0.", ".")}
                        {i !== j && p !== null && p < 0.05 ? "✱" : ""}
                      </text>
                    </g>
                  );
                })}
              </g>
            ))}
          </svg>
        </div>
      )}
    </ChartFrame>
  );
}
