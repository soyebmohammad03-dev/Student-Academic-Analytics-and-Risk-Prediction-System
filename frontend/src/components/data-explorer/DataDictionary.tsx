"use client";

import { useState } from "react";

import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ColumnInfo } from "@/lib/api";
import { cn } from "@/lib/cn";

const ALL = "All";

function allowedText(column: ColumnInfo): string {
  if (column.allowed_values.length) {
    return column.allowed_values.map((v) => `${v.code} = ${v.label}`).join(" · ");
  }
  return `${column.minimum}–${column.maximum}`;
}

function observedText(column: ColumnInfo): string | null {
  const o = column.observed;
  if (!o) return "Not present in this file";
  const range = o.minimum !== null && o.maximum !== null ? `${o.minimum}–${o.maximum}, ` : "";
  return `Observed ${range}${o.unique} distinct ${o.unique === 1 ? "value" : "values"}`;
}

export function DataDictionary({ columns }: { columns?: ColumnInfo[] }) {
  const [group, setGroup] = useState(ALL);

  if (!columns) {
    return (
      <Card className="space-y-3 p-5" aria-busy="true" aria-label="Loading data dictionary">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </Card>
    );
  }

  const groups = [ALL, ...new Set(columns.map((c) => c.group))];
  const visible = group === ALL ? columns : columns.filter((c) => c.group === group);

  return (
    <div className="space-y-3">
      <div
        role="toolbar"
        aria-label="Filter attributes by group"
        className="flex flex-wrap gap-1.5"
      >
        {groups.map((g) => (
          <button
            key={g}
            type="button"
            aria-pressed={g === group}
            onClick={() => setGroup(g)}
            className={cn(
              "h-7 rounded-full px-3 text-[12px] font-medium transition-colors duration-150",
              g === group
                ? "bg-text text-bg"
                : "bg-fill text-text-secondary hover:bg-fill-strong hover:text-text",
            )}
          >
            {g}
          </button>
        ))}
      </div>

      <Card>
        <ul className="divide-y divide-separator">
          {visible.map((column) => (
            <li
              key={column.name}
              className="grid gap-x-6 gap-y-1.5 px-5 py-3.5 sm:grid-cols-[180px_minmax(0,1fr)] sm:px-6"
            >
              <div>
                <p className="font-mono text-[13px] font-medium text-text">{column.name}</p>
                <p className="text-[12px] text-text-secondary">{column.label}</p>
              </div>
              <div className="min-w-0 space-y-1.5">
                <div className="flex flex-wrap items-center gap-1.5">
                  <StatusBadge>
                    {column.measure === "numerical" ? "Numerical" : "Categorical"}
                  </StatusBadge>
                  <StatusBadge>{column.scale}</StatusBadge>
                  {column.role === "target" && <StatusBadge tone="accent">Target</StatusBadge>}
                  {column.role === "prior_grade" && (
                    <StatusBadge tone="caution">Prior grade</StatusBadge>
                  )}
                </div>
                <p className="text-[13px] leading-[19px] text-text">{column.description}</p>
                <p className="text-[12px] leading-[18px] text-text-secondary">
                  <span className="text-text-tertiary">Allowed: </span>
                  {allowedText(column)}
                </p>
                <p className="text-[12px] text-text-tertiary">{observedText(column)}</p>
                {column.notes.map((note) => (
                  <p key={note} className="text-[12px] leading-[18px] text-text-secondary">
                    {note}
                  </p>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
