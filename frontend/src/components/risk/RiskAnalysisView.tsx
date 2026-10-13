"use client";

import { useState } from "react";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Section } from "@/components/ui/Section";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { Skeleton } from "@/components/ui/Skeleton";
import { fmt } from "@/lib/format";
import {
  type ImportanceResult,
  type ModelInterpretation,
  type RiskProfiles,
  type Scenario,
  type SingleProfile,
  type Task,
  scenarioOptions,
  taskOptions,
} from "@/lib/risk";
import { cohortPath } from "@/lib/statistics";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort } from "@/lib/useCohort";

const TOP = 8;

function pct(value: number | null) {
  return value === null ? "—" : `${(100 * value).toFixed(0)}%`;
}

/** Observed at-risk share per group, with its 95% interval and the cohort rate as a line. */
function ProfileChart({ profile, overall }: { profile: SingleProfile; overall: number }) {
  return (
    <ChartFrame
      title={profile.label}
      subtitle={`Cramér's V ${fmt(profile.cramers_v, 2)} (${profile.magnitude}) · BH-adjusted p ${fmt(profile.p_adjusted, 3)}`}
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

/** One importance method on its own scale; methods are never placed on a shared axis. */
function ImportanceCard({ result }: { result: ImportanceResult }) {
  const items = result.items.filter((i) => i.value !== 0).slice(0, TOP);
  const max = Math.max(...items.map((i) => Math.abs(i.value)), 1e-9);
  const signed = result.method === "standardised_coefficient";
  return (
    <ChartFrame
      title={result.method_label}
      subtitle={`${result.unit}. ${result.data}`}
      table={{
        headers: ["Rank", "Feature", "Value", "SD"],
        rows: items.map((i) => [i.rank, i.label, i.value.toFixed(3), fmt(i.std, 3)]),
      }}
    >
      {() => (
        <>
          <ul className="space-y-2" aria-label={result.method_label}>
            {items.map((i) => (
              <li
                key={i.feature}
                className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 text-[12px]"
              >
                <span className="truncate text-text-secondary" title={i.label}>
                  {i.label}
                </span>
                <span className="h-3 rounded-r bg-fill">
                  <span
                    className="block h-full rounded-r"
                    style={{
                      width: `${(100 * Math.abs(i.value)) / max}%`,
                      // Coefficients: sign shown by colour. Other methods: a negative
                      // value means no measurable reliance, so it is drawn muted.
                      background:
                        i.value >= 0
                          ? "var(--chart-1)"
                          : signed
                            ? "var(--chart-2)"
                            : "var(--text-tertiary)",
                    }}
                  />
                </span>
                <span className="text-right text-text tabular-nums">
                  {signed && i.value > 0 ? "+" : ""}
                  {i.value.toFixed(3)}
                </span>
              </li>
            ))}
          </ul>
          <ul className="mt-3 list-disc space-y-1 pl-4 text-[11px] leading-4 text-text-tertiary">
            {result.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </>
      )}
    </ChartFrame>
  );
}

function Loading({ label }: { label: string }) {
  return (
    <div className="grid gap-3 md:grid-cols-2" aria-busy="true" aria-label={label}>
      {Array.from({ length: 2 }, (_, i) => (
        <Skeleton key={i} className="h-56 w-full rounded-2xl" />
      ))}
    </div>
  );
}

export function RiskAnalysisView() {
  const [cohort, setCohort] = useCohort();
  const [task, setTask] = useState<Task>("classification");
  const [scenario, setScenario] = useState<Scenario>("early");
  const [reloadKey, setReloadKey] = useState(0);
  const retry = () => setReloadKey((k) => k + 1);

  const profiles = useApi<RiskProfiles>(cohortPath("/risk/profiles", cohort), reloadKey);
  const importance = useApi<ModelInterpretation>(
    cohortPath("/interpretability/importance", cohort, { task, scenario }),
    reloadKey,
  );
  const p = profiles.data?.cohort === cohort ? profiles.data : undefined;
  const imp =
    importance.data?.cohort === cohort &&
    importance.data.task === task &&
    importance.data.scenario === scenario
      ? importance.data
      : undefined;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Modelling · Phase 6"
        title="Risk Analysis"
        description="Observed academic risk across student groups, and which inputs the selected models rely on. Academic risk means a final grade below 10; it is not dropout. Nothing here is causal or a judgement about an individual."
      >
        <SegmentedControl
          label="Cohort"
          options={cohortOptions}
          value={cohort}
          onChange={setCohort}
          className="mt-6"
        />
      </PageHeader>

      <Section
        title="Group-level risk profiles"
        description="Share of students below the pass mark in each group, with 95% intervals (black line). The grey mark is the cohort rate. These describe groups in one historical dataset, not any student."
      >
        {profiles.error ? (
          <DataUnavailable error={profiles.error} onRetry={retry} />
        ) : !p ? (
          <Loading label="Loading risk profiles" />
        ) : (
          <>
            <p className="mb-4 px-1 text-[14px] text-text">
              {p.at_risk} of {p.n} students ({p.risk_percent.toFixed(1)}%) had a final grade below{" "}
              {p.threshold}.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {p.single.map((s) => (
                <ProfileChart key={s.variable} profile={s} overall={p.risk_percent} />
              ))}
            </div>
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
        title="What the selected models rely on"
        description="Global importance for the model selected in Phase 5. Each method answers a different question and has its own unit, so values are not compared across methods."
      >
        <div className="mb-4 flex flex-wrap gap-3">
          <SegmentedControl label="Task" options={taskOptions} value={task} onChange={setTask} />
          <SegmentedControl
            label="Scenario"
            options={scenarioOptions}
            value={scenario}
            onChange={setScenario}
          />
        </div>
        {importance.error ? (
          <DataUnavailable error={importance.error} onRetry={retry} />
        ) : !imp ? (
          <Loading label="Loading feature importance" />
        ) : (
          <>
            <p className="mb-4 px-1 text-[14px] text-text">
              Selected model: <span className="font-semibold">{imp.model_label}</span>
            </p>
            <div className="grid gap-3 lg:grid-cols-2">
              {imp.methods.map((m) => (
                <ImportanceCard key={m.method_label} result={m} />
              ))}
            </div>
            {imp.calibration && (
              <Card className="mt-3 p-5 text-[13px] leading-5 text-text-secondary">
                <p className="text-text">
                  Probability check on the test set: mean predicted{" "}
                  {imp.calibration.mean_predicted.toFixed(2)} vs observed{" "}
                  {imp.calibration.observed_rate.toFixed(2)} (Brier{" "}
                  {imp.calibration.brier.toFixed(3)}, n = {imp.calibration.n}).
                </p>
                <p className="mt-1">{imp.calibration.note}</p>
              </Card>
            )}
          </>
        )}
      </Section>
    </div>
  );
}
