"use client";

import { MetricCard as Figure } from "@/components/ui/MetricCard";
import { useState } from "react";

import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import { Skeleton } from "@/components/ui/Skeleton";
import { fmt, fmtP, fmtPercent } from "@/lib/format";
import {
  type Associations,
  type Correlations,
  type DescriptiveStatistics,
  type Distributions,
  type GroupComparison,
  type Outliers,
  type ResearchQuestions as RQ,
  cohortPath,
} from "@/lib/statistics";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort } from "@/lib/useCohort";

import { GroupComparisonView } from "./GroupComparisonView";
import { ResearchQuestions } from "./ResearchQuestions";

function forCohort<T extends { cohort: string }>(data: T | undefined, cohort: string) {
  return data?.cohort === cohort ? data : undefined;
}

function Loading({ height = "h-40" }: { height?: string }) {
  return <Skeleton className={`${height} w-full rounded-2xl`} />;
}

export function StatisticsView() {
  const [cohort, setCohort] = useCohort();
  const [variable, setVariable] = useState("studytime");
  const [reloadKey, setReloadKey] = useState(0);

  const distributions = useApi<Distributions>(
    cohortPath("/statistics/distributions", cohort),
    reloadKey,
  );
  const research = useApi<RQ>(cohortPath("/statistics/hypothesis-tests", cohort), reloadKey);
  const correlations = useApi<Correlations>(
    cohortPath("/statistics/correlations", cohort),
    reloadKey,
  );
  const associations = useApi<Associations>(
    cohortPath("/statistics/associations", cohort),
    reloadKey,
  );
  const descriptive = useApi<DescriptiveStatistics>(
    cohortPath("/statistics/descriptive", cohort),
    reloadKey,
  );
  const outliers = useApi<Outliers>(cohortPath("/statistics/outliers", cohort), reloadKey);
  const comparison = useApi<GroupComparison>(
    cohortPath("/statistics/group-comparisons", cohort, { variable }),
    reloadKey,
  );

  const error = distributions.error ?? research.error ?? descriptive.error;
  const dist = forCohort(distributions.data, cohort);
  const g3 = dist?.grades.find((g) => g.variable === "G3");
  // Comparisons carry no cohort field, so hide stale data while a new request loads.
  const cmp =
    !comparison.loading && comparison.data?.variable === variable ? comparison.data : undefined;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Analysis"
        title="Statistical Analysis"
        description="Descriptive statistics, correlations and hypothesis tests on the validated data. Every result describes an association in these students' records, never a cause."
      >
        <Toolbar className="mt-6">
          <ToolbarItem label="Cohort">
            <SegmentedControl
              label="Cohort"
              options={cohortOptions}
              value={cohort}
              onChange={setCohort}
            />
          </ToolbarItem>
        </Toolbar>
      </PageHeader>

      {error ? (
        <DataUnavailable error={error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : (
        <>
          <Section
            title="Final grade at a glance"
            description="G3 on the 0–20 scale; all students included."
          >
            {!g3 || !dist ? (
              <Loading height="h-28" />
            ) : (
              <div className="space-y-3">
                <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl bg-separator shadow-card sm:grid-cols-3 xl:grid-cols-5">
                  <Figure
                    label="Mean"
                    value={fmt(g3.summary.mean)}
                    hint={`95% CI ${fmt(g3.summary.mean_ci.low)}–${fmt(g3.summary.mean_ci.high)}`}
                  />
                  <Figure
                    label="Median"
                    value={fmt(g3.summary.median, 0)}
                    hint={`IQR ${g3.summary.q1}–${g3.summary.q3}`}
                  />
                  <Figure
                    label="Std. deviation"
                    value={fmt(g3.summary.std)}
                    hint={`n = ${g3.summary.n}`}
                  />
                  <Figure
                    label="At academic risk"
                    value={fmtPercent(100 * dist.risk.proportion)}
                    hint={`${dist.risk.at_risk} students · 95% CI ${fmtPercent(100 * (dist.risk.proportion_ci.low ?? 0))}–${fmtPercent(100 * (dist.risk.proportion_ci.high ?? 0))}`}
                  />
                  <Figure
                    label="Final grade of 0"
                    value={String(g3.zero_count)}
                    hint="kept in all analyses"
                  />
                </dl>
                <Card className="space-y-1.5 px-5 py-4 text-[13px] leading-[19px] text-text-secondary">
                  <p className="text-text">{g3.shape.description}</p>
                  {dist.observations.map((o) => (
                    <p key={o}>{o}</p>
                  ))}
                </Card>
              </div>
            )}
          </Section>

          <Section
            title="Research questions"
            description="Pre-specified confirmatory tests (Holm-adjusted) and exploratory summaries."
          >
            {forCohort(research.data, cohort) ? (
              <ResearchQuestions data={research.data!} />
            ) : (
              <Loading height="h-96" />
            )}
          </Section>

          <Section
            title="Group comparisons"
            description="Final grade across groups, with the test chosen from assumption checks."
          >
            <GroupComparisonView variable={variable} onVariable={setVariable} comparison={cmp} />
          </Section>

          <Section
            title="Correlations with G3"
            description="Spearman unless both variables are interval-scaled and approximately normal."
          >
            {!forCohort(correlations.data, cohort) ? (
              <Loading />
            ) : (
              <DataTable
                caption="Key correlations with the final grade"
                rows={correlations.data!.key_pairs.map((c, i) => ({
                  c,
                  s: correlations.data!.sensitivity_key_pairs[i],
                }))}
                rowKey={(r) => r.c.x}
                columns={[
                  { header: "Variable", cell: (r) => r.c.x_label },
                  { header: "Method", cell: (r) => r.c.method },
                  { header: "r", cell: (r) => fmt(r.c.r), align: "right" },
                  {
                    header: "95% CI",
                    cell: (r) => `${fmt(r.c.r_ci.low)} to ${fmt(r.c.r_ci.high)}`,
                    align: "right",
                  },
                  { header: "n", cell: (r) => r.c.n, align: "right" },
                  { header: "Holm p", cell: (r) => fmtP(r.c.p_adjusted), align: "right" },
                  { header: "Strength", cell: (r) => r.c.strength },
                  {
                    header: "Without G3 = 0",
                    cell: (r) => `${fmt(r.s.r)} (n = ${r.s.n})`,
                    align: "right",
                  },
                ]}
              />
            )}
          </Section>

          <Section
            title="Associations with academic risk"
            description="Chi-square or Fisher's exact test; Cramér's V; Benjamini–Hochberg adjusted (exploratory)."
          >
            {!forCohort(associations.data, cohort) ? (
              <Loading />
            ) : (
              <DataTable
                caption="Categorical associations with academic risk"
                rows={[...associations.data!.items].sort(
                  (a, b) => (b.cramers_v ?? 0) - (a.cramers_v ?? 0),
                )}
                rowKey={(r) => r.variable}
                columns={[
                  { header: "Variable", cell: (r) => r.label },
                  {
                    header: "Share at risk by group",
                    cell: (r) =>
                      r.rows
                        .map(
                          (row) => `${row.label}: ${row.risk_percent.toFixed(0)}% (n = ${row.n})`,
                        )
                        .join(" · "),
                    className: "text-[12px] text-text-secondary min-w-[18rem]",
                  },
                  { header: "Test", cell: (r) => r.test, className: "whitespace-nowrap" },
                  {
                    header: "Cramér's V",
                    cell: (r) => `${fmt(r.cramers_v)} · ${r.magnitude}`,
                    align: "right",
                  },
                  { header: "BH p", cell: (r) => fmtP(r.p_adjusted), align: "right" },
                ]}
              />
            )}
          </Section>

          <Section
            title="Descriptive statistics"
            description="Numerically coded variables. Ordinal codes are best read by median and quartiles."
          >
            {!forCohort(descriptive.data, cohort) ? (
              <Loading />
            ) : (
              <DataTable
                caption="Descriptive statistics"
                rows={descriptive.data!.numeric}
                rowKey={(r) => r.variable}
                columns={[
                  {
                    header: "Variable",
                    cell: (r) => (
                      <span title={r.note ?? undefined}>
                        {r.label}
                        {r.scale === "ordinal" && (
                          <span className="text-text-tertiary"> · ordinal</span>
                        )}
                      </span>
                    ),
                  },
                  { header: "n", cell: (r) => r.n, align: "right" },
                  { header: "Mean", cell: (r) => fmt(r.mean), align: "right" },
                  { header: "Median", cell: (r) => fmt(r.median, 1), align: "right" },
                  { header: "Mode", cell: (r) => r.modes.join(", "), align: "right" },
                  { header: "SD", cell: (r) => fmt(r.std), align: "right" },
                  { header: "Variance", cell: (r) => fmt(r.variance), align: "right" },
                  { header: "Min–max", cell: (r) => `${r.minimum}–${r.maximum}`, align: "right" },
                  { header: "Q1–Q3", cell: (r) => `${r.q1}–${r.q3}`, align: "right" },
                  { header: "IQR", cell: (r) => fmt(r.iqr, 1), align: "right" },
                  { header: "Skew", cell: (r) => fmt(r.skewness), align: "right" },
                ]}
              />
            )}
          </Section>

          <Section
            title="Outlier screening"
            description="Flagged by Tukey fences; an outlier is not an error and nothing is removed."
          >
            {!forCohort(outliers.data, cohort) ? (
              <Loading />
            ) : (
              <DataTable
                caption="Outlier screening"
                rows={outliers.data!.items}
                rowKey={(r) => r.variable}
                columns={[
                  { header: "Variable", cell: (r) => r.label },
                  {
                    header: "Fences",
                    cell: (r) => `${fmt(r.lower_fence, 1)} to ${fmt(r.upper_fence, 1)}`,
                    align: "right",
                  },
                  { header: "Below", cell: (r) => r.below, align: "right" },
                  { header: "Above", cell: (r) => r.above, align: "right" },
                  {
                    header: "Share flagged",
                    cell: (r) => fmtPercent(100 * r.proportion),
                    align: "right",
                  },
                  { header: "|z| > 3", cell: (r) => r.z_count, align: "right" },
                ]}
              />
            )}
          </Section>
        </>
      )}
    </div>
  );
}
