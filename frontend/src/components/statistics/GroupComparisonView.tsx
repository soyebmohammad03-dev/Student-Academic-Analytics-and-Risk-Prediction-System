"use client";

import { BoxPlot } from "@/components/charts/BoxPlot";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fmt, fmtP } from "@/lib/format";
import type { BoxPlotData, GroupComparison } from "@/lib/statistics";

export const COMPARISON_OPTIONS = [
  { value: "studytime", label: "Weekly study time" },
  { value: "has_past_failures", label: "Any past failures" },
  { value: "failures", label: "Number of past failures" },
  { value: "absence_band", label: "Absence band" },
  { value: "Medu", label: "Mother's education" },
  { value: "Fedu", label: "Father's education" },
  { value: "schoolsup", label: "School support" },
  { value: "famsup", label: "Family support" },
  { value: "paid", label: "Extra paid classes" },
  { value: "sex", label: "Sex" },
  { value: "higher", label: "Wants higher education" },
  { value: "internet", label: "Internet at home" },
  { value: "address", label: "Home address type" },
] as const;

function toBoxPlot(c: GroupComparison): BoxPlotData {
  return {
    variable: c.variable,
    variable_label: c.variable_label,
    outcome: c.outcome,
    groups: c.groups.map((g) => g.box),
  };
}

export function GroupComparisonView({
  variable,
  onVariable,
  comparison,
}: {
  variable: string;
  onVariable: (v: string) => void;
  comparison?: GroupComparison;
}) {
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-3 text-[13px] text-text-secondary">
        Compare G3 by
        <select
          value={variable}
          onChange={(e) => onVariable(e.target.value)}
          className="h-8 rounded-lg bg-fill px-2.5 text-[13px] text-text focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
        >
          {COMPARISON_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>

      {!comparison ? (
        <Skeleton className="h-64 w-full rounded-2xl" />
      ) : (
        <>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
            <BoxPlot data={toBoxPlot(comparison)} />
            <Card className="space-y-3 p-5 text-[13px]">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-text">{comparison.test}</p>
                <StatusBadge>{comparison.family}</StatusBadge>
                {comparison.significant ? (
                  <StatusBadge tone="accent">p &lt; .05</StatusBadge>
                ) : (
                  <StatusBadge>p ≥ .05</StatusBadge>
                )}
              </div>
              <p className="text-text-secondary tabular-nums">
                {comparison.statistic_name} = {fmt(comparison.statistic)}
                {comparison.df && <> (df {comparison.df})</>}, p = {fmtP(comparison.p)}
              </p>
              <ul className="space-y-1 text-text tabular-nums">
                {comparison.effect_sizes.map((e) => (
                  <li key={e.name}>
                    {e.name} = {fmt(e.value)}
                    {e.ci && e.ci.low !== null && (
                      <span className="text-text-secondary">
                        {" "}
                        [{fmt(e.ci.low)}, {fmt(e.ci.high)}]
                      </span>
                    )}{" "}
                    <span className="text-text-secondary">· {e.magnitude}</span>
                  </li>
                ))}
              </ul>
              <p className="text-[12px] leading-[18px] text-text-secondary">
                {comparison.rationale}
              </p>
              <p className="text-[12px] text-text-secondary">
                Variances: {comparison.variance.test}, p = {fmtP(comparison.variance.p)} (
                {comparison.variance.equal_variances ? "equal" : "unequal"}).
              </p>
              {comparison.warnings.map((w) => (
                <p key={w} className="text-[12px] text-caution">
                  {w}
                </p>
              ))}
              <p className="text-[12px] text-text-tertiary">
                This exploratory comparison is not adjusted for the other comparisons on this page.
              </p>
            </Card>
          </div>

          <DataTable
            caption="Assumption checks per group"
            rows={comparison.normality}
            rowKey={(r) => r.group}
            columns={[
              { header: "Group", cell: (r) => r.group },
              { header: "n", cell: (r) => r.n, align: "right" },
              { header: "Shapiro–Wilk p", cell: (r) => fmtP(r.shapiro_p), align: "right" },
              { header: "Skewness", cell: (r) => fmt(r.skewness), align: "right" },
              {
                header: "Mean-based test adequate",
                cell: (r) => (r.adequate ? "Yes" : "No"),
                className: "whitespace-nowrap",
              },
              {
                header: "Basis",
                cell: (r) => r.basis,
                className: "text-text-secondary text-[12px]",
              },
            ]}
          />

          {comparison.posthoc.length > 0 && (
            <DataTable
              caption="Post-hoc comparisons"
              rows={comparison.posthoc}
              rowKey={(r) => `${r.group_a}-${r.group_b}`}
              columns={[
                { header: "Comparison", cell: (r) => `${r.group_a} vs ${r.group_b}` },
                {
                  header: comparison.posthoc_method?.startsWith("Dunn") ? "z" : "Mean diff.",
                  cell: (r) => fmt(r.estimate),
                  align: "right",
                },
                { header: "Adjusted p", cell: (r) => fmtP(r.p_adjusted), align: "right" },
                {
                  header: comparison.posthoc_method ?? "",
                  cell: (r) => (r.significant ? "Differs" : "—"),
                },
              ]}
            />
          )}
        </>
      )}
    </div>
  );
}
