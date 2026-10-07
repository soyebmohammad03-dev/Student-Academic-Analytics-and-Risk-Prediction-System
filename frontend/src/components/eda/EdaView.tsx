"use client";

import { useState } from "react";

import { BarList } from "@/components/charts/BarList";
import { BoxPlot } from "@/components/charts/BoxPlot";
import { Heatmap } from "@/components/charts/Heatmap";
import { Histogram } from "@/components/charts/Histogram";
import { Scatter } from "@/components/charts/Scatter";
import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { Section } from "@/components/ui/Section";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { Skeleton } from "@/components/ui/Skeleton";
import { fmt } from "@/lib/format";
import { type Eda, cohortPath } from "@/lib/statistics";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort } from "@/lib/useCohort";

const RISK_THRESHOLD = 10;

export function EdaView() {
  const [cohort, setCohort] = useCohort();
  const [reloadKey, setReloadKey] = useState(0);
  const eda = useApi<Eda>(cohortPath("/eda/charts", cohort), reloadKey);
  const data = eda.data?.cohort === cohort ? eda.data : undefined;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Analysis · Phase 4"
        title="Exploratory Data Analysis"
        description="Distributions, relationships and profiles computed from every student in the cohort. Patterns shown here are descriptive and do not imply cause."
      >
        <SegmentedControl
          label="Cohort"
          options={cohortOptions}
          value={cohort}
          onChange={setCohort}
          className="mt-6"
        />
      </PageHeader>

      {eda.error ? (
        <DataUnavailable error={eda.error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : !data ? (
        <div className="grid gap-3 md:grid-cols-2" aria-busy="true" aria-label="Loading charts">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-64 w-full rounded-2xl" />
          ))}
        </div>
      ) : (
        <>
          <Section
            title="Grade distributions"
            description={`Orange bars are below the pass mark of ${RISK_THRESHOLD} (academic risk). Zero grades are included.`}
          >
            <div className="grid gap-3 md:grid-cols-2">
              {data.histograms
                .filter((h) => h.variable.startsWith("G"))
                .map((h) => (
                  <Histogram key={h.variable} data={h} highlightBelow={RISK_THRESHOLD} />
                ))}
              {data.histograms
                .filter((h) => !h.variable.startsWith("G"))
                .map((h) => (
                  <Histogram
                    key={h.variable}
                    data={h}
                    subtitle={`n = ${h.n} · bins of 5 absences`}
                  />
                ))}
            </div>
          </Section>

          <Section title="Student characteristics" description="Counts and shares per category.">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.bars.map((b) => (
                <BarList key={b.variable} data={b} />
              ))}
            </div>
          </Section>

          <Section
            title="Final grade by group"
            description="Box plots of G3. Group differences are tested on the Statistical Analysis page."
          >
            <div className="grid gap-3 lg:grid-cols-2">
              {data.boxplots.map((b) => (
                <BoxPlot key={b.variable} data={b} />
              ))}
            </div>
          </Section>

          <Section
            title="Relationships with the final grade"
            description="Interim grades track G3 closely; absences show a weaker, noisier pattern."
          >
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.scatters.map((s) => (
                <Scatter key={s.x} data={s} />
              ))}
            </div>
          </Section>

          <Section
            title="Correlation structure"
            description="Pairwise Spearman correlations between numeric variables."
          >
            <Heatmap data={data.heatmap} />
          </Section>

          <Section
            title="Academic-risk profile"
            description="Students at risk (G3 < 10) compared with the rest. Standardised difference is Cohen's d."
          >
            <DataTable
              caption="Profile of at-risk and not-at-risk students"
              rows={data.risk_profile}
              rowKey={(r) => r.variable}
              columns={[
                { header: "Variable", cell: (r) => r.label },
                { header: "Statistic", cell: (r) => (r.statistic === "mean" ? "Mean" : "% yes") },
                {
                  header: "At risk",
                  cell: (r) => fmt(r.at_risk, r.statistic === "mean" ? 2 : 1),
                  align: "right",
                },
                {
                  header: "Not at risk",
                  cell: (r) => fmt(r.not_at_risk, r.statistic === "mean" ? 2 : 1),
                  align: "right",
                },
                {
                  header: "Std. difference",
                  cell: (r) => fmt(r.standardised_difference),
                  align: "right",
                },
              ]}
            />
          </Section>

          <Section
            title="Study time and past failures together"
            description="Mean G3 for each combination, with group sizes. Small cells are imprecise."
          >
            <DataTable
              caption="Mean final grade by study time and past failures"
              rows={data.crosstab.row_labels}
              rowKey={(r) => r}
              columns={[
                { header: "Weekly study time", cell: (r) => r },
                ...data.crosstab.column_labels.map((col) => ({
                  header: col,
                  align: "right" as const,
                  cell: (row: string) => {
                    const c = data.crosstab.cells.find((x) => x.row === row && x.column === col);
                    return c && c.n ? (
                      <>
                        {fmt(c.mean)} <span className="text-text-tertiary">(n = {c.n})</span>
                      </>
                    ) : (
                      "—"
                    );
                  },
                })),
              ]}
            />
          </Section>
        </>
      )}
    </div>
  );
}
