"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useState } from "react";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { Callout, KindBadge } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { MetricCard, MetricGrid } from "@/components/ui/MetricCard";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import { LoadingBlock } from "@/components/ui/States";
import { withQuery } from "@/lib/api";
import { fmt, fmtInterval, fmtP, fmtShare } from "@/lib/format";
import { type ScenarioComparison, metricInfo } from "@/lib/models";
import type { RiskProfiles, SingleProfile } from "@/lib/risk";
import { cohortPath } from "@/lib/statistics";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort } from "@/lib/useCohort";

function pct(value: number | null) {
  return value === null ? "—" : `${(100 * value).toFixed(0)}%`;
}

/** Observed at-risk share per group, with its 95% interval and the cohort rate as a line. */
function ProfileChart({ profile, overall }: { profile: SingleProfile; overall: number }) {
  return (
    <ChartFrame
      title={profile.label}
      subtitle={`Cramér's V ${fmt(profile.cramers_v, 2)} (${profile.magnitude}) · BH-adjusted p ${fmtP(profile.p_adjusted)}`}
      table={{
        headers: ["Group", "Students", "At risk", "Share", "95% CI"],
        rows: profile.groups.map((g) => [
          g.label,
          g.n,
          g.at_risk,
          `${g.risk_percent.toFixed(1)}%`,
          `${pct(g.risk_ci.low)}–${pct(g.risk_ci.high)}`,
        ]),
      }}
    >
      {() => (
        <ul className="space-y-2.5" aria-label={`Academic risk by ${profile.label}`}>
          {profile.groups.map((g) => (
            <li
              key={g.key}
              className="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)_4.5rem] items-center gap-3 text-[12px]"
            >
              <span className="truncate text-text-secondary" title={g.label}>
                {g.label}
              </span>
              <span className="relative h-3 rounded-r bg-fill">
                <span
                  className="absolute inset-y-0 left-0 rounded-r"
                  style={{ width: `${g.risk_percent}%`, background: "var(--chart-2)" }}
                />
                <span
                  className="absolute top-1/2 h-px -translate-y-1/2 bg-text"
                  style={{
                    left: `${100 * (g.risk_ci.low ?? 0)}%`,
                    width: `${100 * ((g.risk_ci.high ?? 0) - (g.risk_ci.low ?? 0))}%`,
                  }}
                  aria-hidden
                />
                <span
                  className="absolute inset-y-[-3px] w-px bg-text-tertiary"
                  style={{ left: `${overall}%` }}
                  aria-hidden
                />
              </span>
              <span className="text-right leading-4 text-text tabular-nums">
                {g.risk_percent.toFixed(0)}%
                <span className="block text-[11px] text-text-tertiary">
                  n = {g.n}
                  {g.reliable ? "" : " · few"}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </ChartFrame>
  );
}

type Pair = RiskProfiles["pairs"][number];

/** Two-way table of observed shares; cells with fewer than 10 students are muted. */
function PairTable({ pair }: { pair: Pair }) {
  const rows = [...new Set(pair.cells.map((c) => c.row))];
  const cols = [...new Set(pair.cells.map((c) => c.column))];
  const cell = (r: string, c: string) => pair.cells.find((x) => x.row === r && x.column === c);
  const label = (key: string, kind: "row" | "column") => {
    const found = pair.cells.find((x) => x[kind] === key);
    return found ? (kind === "row" ? found.row_label : found.column_label) : key;
  };
  return (
    <Card className="p-4 sm:p-5">
      <p className="text-[14px] font-semibold text-text">
        {pair.rows_label} × {pair.columns_label}
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[320px] border-separate border-spacing-1 text-[12px] tabular-nums">
          <caption className="sr-only">
            Observed share below the pass mark by {pair.rows_label} and {pair.columns_label}
          </caption>
          <thead>
            <tr className="text-[11px] text-text-tertiary">
              <th scope="col" className="text-left font-medium">
                {pair.rows_label} ↓
              </th>
              {cols.map((c) => (
                <th key={c} scope="col" className="font-medium">
                  {label(c, "column")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r}>
                <th scope="row" className="pr-2 text-left font-medium text-text-secondary">
                  {label(r, "row")}
                </th>
                {cols.map((c) => {
                  const x = cell(r, c);
                  if (!x) return <td key={c} />;
                  const share = x.risk_percent ?? 0;
                  return (
                    <td
                      key={c}
                      className="rounded-lg px-2 py-2 text-center"
                      title={`${x.at_risk} of ${x.n} · 95% CI ${fmtInterval(x.risk_ci)}`}
                      style={{
                        background: x.reliable
                          ? `color-mix(in srgb, var(--chart-2) ${Math.round(6 + 0.5 * share)}%, transparent)`
                          : "var(--fill)",
                      }}
                    >
                      <span className={x.reliable ? "text-text" : "text-text-tertiary"}>
                        {x.risk_percent === null ? "—" : `${x.risk_percent.toFixed(0)}%`}
                      </span>
                      <span className="block text-[10px] text-text-tertiary">
                        n = {x.n}
                        {x.reliable ? "" : " · few"}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/** Selected classifiers' held-out ability to find students below the pass mark. */
function ModelDerived({ data }: { data: ScenarioComparison }) {
  return (
    <div className="overflow-x-auto rounded-2xl bg-surface shadow-card">
      <table className="w-full min-w-[560px] text-left text-[13px]">
        <caption className="sr-only">Held-out test performance of the selected classifiers</caption>
        <thead>
          <tr className="border-b border-separator bg-surface-muted text-[11px] text-text-tertiary">
            <th scope="col" className="px-4 py-2.5 font-medium">
              Scenario · selected model
            </th>
            {(["recall", "precision", "f1", "roc_auc"] as const).map((m) => (
              <th key={m} scope="col" className="px-4 py-2.5 text-right font-medium">
                <span className="inline-flex items-center gap-1">
                  {metricInfo[m].short}
                  <InfoTip label={`What is ${metricInfo[m].label}?`}>
                    {metricInfo[m].definition}
                  </InfoTip>
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-separator">
          {data.rows.map((r) => (
            <tr key={r.scenario}>
              <th scope="row" className="px-4 py-2.5 font-medium text-text">
                {r.label}
                <span className="block text-[12px] font-normal text-text-secondary">
                  {r.selected_label}
                </span>
              </th>
              {(["recall", "precision", "f1", "roc_auc"] as const).map((m) => (
                <td key={m} className="px-4 py-2.5 text-right text-text tabular-nums">
                  {m === "recall" || m === "precision" ? fmtShare(r.test[m]) : fmt(r.test[m], 2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RiskAnalysisView() {
  const [cohort, setCohort] = useCohort();
  const [reloadKey, setReloadKey] = useState(0);
  const retry = () => setReloadKey((k) => k + 1);

  const profiles = useApi<RiskProfiles>(cohortPath("/risk/profiles", cohort), reloadKey);
  const classifiers = useApi<ScenarioComparison>(
    withQuery("/models/scenario-comparison", { cohort, task: "classification" }),
    reloadKey,
  );
  const p = profiles.data?.cohort === cohort ? profiles.data : undefined;
  const models = classifiers.data?.cohort === cohort ? classifiers.data : undefined;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Modelling"
        title="Risk Analysis"
        description="Observed academic risk across school-related student groups, with sample sizes and uncertainty. Nothing here is causal or a judgement about an individual."
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

      <Section title="Definition" action={<KindBadge kind="observed" />}>
        {profiles.error ? (
          <DataUnavailable error={profiles.error} onRetry={retry} />
        ) : !p ? (
          <LoadingBlock label="Loading the cohort rate" height="h-28" />
        ) : (
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
            <MetricGrid label="Observed academic risk">
              <MetricCard
                label="Below the pass mark"
                value={`${p.risk_percent.toFixed(1)}%`}
                hint={`${p.at_risk} of ${p.n} · 95% CI ${fmtInterval(p.risk_ci, 1)}`}
              />
              <MetricCard label="Pass mark" value={p.threshold} unit="/ 20" hint="Final grade G3" />
            </MetricGrid>
            <Card className="p-5 text-[13px] leading-5 text-text-secondary">
              <p>
                <span className="font-medium text-text">Academic risk</span> means a final grade G3
                below {p.threshold} of 20 in the historical data. It is not dropout — the dataset
                has no dropout outcome — and these figures are observed proportions, not
                predictions.
              </p>
              <p className="mt-2">
                No low/medium/high bands are used: there are no validated educational thresholds for
                them. Demographic groups are not profiled here, so that no demographic group is
                labelled as at risk.
              </p>
            </Card>
          </div>
        )}
      </Section>

      <Section
        title="Group-level risk profiles"
        description="Share of students below the pass mark in each group, with 95% intervals (black line). The grey mark is the cohort rate. Groups with fewer than 10 students are marked “few”."
        action={<KindBadge kind="observed" />}
      >
        {profiles.error ? null : !p ? (
          <LoadingBlock label="Loading risk profiles" count={2} height="h-56" />
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-2">
              {p.single.map((s) => (
                <ProfileChart key={s.variable} profile={s} overall={p.risk_percent} />
              ))}
            </div>
            {p.pairs.length > 0 && (
              <>
                <h3 className="mt-8 mb-3 px-1 text-[14px] font-semibold text-text">
                  Two-way tables
                </h3>
                <div className="grid gap-3 lg:grid-cols-2">
                  {p.pairs.map((pair) => (
                    <PairTable key={`${pair.rows_variable}-${pair.columns_variable}`} pair={pair} />
                  ))}
                </div>
              </>
            )}
            <Card className="mt-3 p-5">
              <ul className="list-disc space-y-1.5 pl-4 text-[13px] leading-5 text-text-secondary">
                {p.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </Card>
          </>
        )}
      </Section>

      <Section
        title="What the models add"
        description="Model-derived and kept separate from the observed statistics above: how often each scenario's selected classifier found the held-out students who finished below the pass mark."
        action={<KindBadge kind="model_evaluation" />}
      >
        {classifiers.error ? (
          <DataUnavailable error={classifiers.error} onRetry={retry} />
        ) : !models ? (
          <LoadingBlock label="Loading classifier results" height="h-40" />
        ) : (
          <>
            <ModelDerived data={models} />
            <p className="mt-3 px-1 text-[12px] leading-[18px] text-text-tertiary">
              Recall below 100% means some students who finished below the pass mark were not
              flagged. A model flag is a prompt for a conversation, never a decision.
            </p>
          </>
        )}
      </Section>

      <Section title="Suggestions for human review">
        <Callout tone="responsible">
          <p>
            For a single record, the Prediction page lists general suggestions for a teacher or
            adviser to consider together with the student — for example reviewing study routines or
            looking at attendance patterns. A suggestion appears only when this cohort&apos;s data
            show a higher observed at-risk share for the triggering group (Fisher&apos;s exact test,
            exploratory); otherwise it is withheld and the evidence is shown. Suggestions are never
            punitive or disciplinary, never clinical or family judgements, and are not triggered by
            demographic or family attributes.
          </p>
          <Link
            href="/prediction"
            className="mt-2 inline-flex items-center gap-1 text-accent hover:underline"
          >
            Open the prediction page <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </Callout>
      </Section>
    </div>
  );
}
