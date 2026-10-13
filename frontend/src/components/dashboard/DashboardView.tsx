"use client";

import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { useState } from "react";

import { GradeStrip } from "@/components/charts/GradeStrip";
import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { SystemStatus } from "@/components/status/SystemStatus";
import { Callout, KindBadge } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { GroupedList, IconTile, ListRow } from "@/components/ui/GroupedList";
import { InfoTip } from "@/components/ui/InfoTip";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import { EmptyState, LoadingBlock } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  type CohortOverview,
  type DashboardSummary,
  type PipelineSummary,
  type SelectedModelSummary,
  withQuery,
} from "@/lib/api";
import { fmt, fmtDate, fmtInterval, fmtP, fmtPercent } from "@/lib/format";
import { metricInfo, scenarioInfo } from "@/lib/models";
import { allModules } from "@/lib/modules";
import { type Scenario, scenarioOptions } from "@/lib/risk";
import { site } from "@/lib/site";
import { type Distributions, type ResearchQuestions, cohortPath } from "@/lib/statistics";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort, useScenario } from "@/lib/useCohort";

const scenarios: Scenario[] = ["early", "mid_year", "full_history"];

function CohortCard({ overview }: { overview: CohortOverview }) {
  const risk = overview.observed_risk;
  const g3 = overview.final_grade;
  const distributions = useApi<Distributions>(
    cohortPath("/statistics/distributions", overview.cohort),
  );
  const counts = distributions.data?.grades.find((g) => g.variable === "G3")?.counts;
  const clean =
    overview.missing_values === 0 && overview.duplicate_rows === 0 && overview.invalid_values === 0;

  return (
    <Card className="flex flex-col p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-[17px] font-semibold tracking-[-0.01em] text-text">
            {overview.subject}
          </h3>
          <p className="mt-0.5 text-[13px] text-text-secondary tabular-nums">
            {overview.rows} students · {overview.columns} attributes
          </p>
        </div>
        <StatusBadge tone={overview.validation_status === "pass" ? "positive" : "caution"}>
          Validation {overview.validation_status}
        </StatusBadge>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-4">
        <div>
          <dt className="flex items-center gap-1 text-[12px] font-medium text-text-secondary">
            Below the pass mark
            <InfoTip label="About the observed at-risk share">{risk.definition}</InfoTip>
          </dt>
          <dd className="mt-1 font-display text-[26px] leading-none font-semibold tracking-[-0.02em] text-text tabular-nums">
            {fmtPercent(risk.percent)}
          </dd>
          <dd className="mt-1.5 text-[11px] text-text-tertiary tabular-nums">
            {risk.at_risk} of {risk.n} · 95% CI {fmtInterval(risk.ci, 1)}
          </dd>
        </div>
        <div>
          <dt className="text-[12px] font-medium text-text-secondary">Final grade (G3)</dt>
          <dd className="mt-1 font-display text-[26px] leading-none font-semibold tracking-[-0.02em] text-text tabular-nums">
            {fmt(g3.mean, 1)}
            <span className="ml-1 text-[14px] font-medium text-text-tertiary">mean</span>
          </dd>
          <dd className="mt-1.5 text-[11px] text-text-tertiary tabular-nums">
            median {fmt(g3.median, 0)} · SD {fmt(g3.std, 1)} · range {g3.minimum}–{g3.maximum}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        {distributions.error ? null : counts ? (
          <GradeStrip
            counts={counts}
            passMark={10}
            label={`${overview.subject} final-grade distribution: ${risk.at_risk} of ${risk.n} students below 10, ${g3.zero_count} with a grade of 0.`}
          />
        ) : (
          <div className="h-[84px] animate-pulse rounded-lg bg-fill" aria-hidden />
        )}
        <p className="mt-2 text-[11px] leading-4 text-text-tertiary">
          Final grades 0–20; orange columns are below the pass mark of 10. {g3.zero_count} students
          have G3 = 0 and are kept in every analysis.
        </p>
      </div>

      <p className="mt-4 border-t border-separator pt-3 text-[12px] text-text-secondary tabular-nums">
        Data quality:{" "}
        {clean
          ? "no missing, duplicate or invalid values"
          : `${overview.missing_values} missing · ${overview.duplicate_rows} duplicate rows · ${overview.invalid_values} invalid`}
      </p>
    </Card>
  );
}

function ModelCell({ item }: { item: SelectedModelSummary | undefined }) {
  if (!item) return <span className="text-text-tertiary">—</span>;
  const info = metricInfo[item.metric];
  return (
    <div className="min-w-0">
      <p className="truncate text-[12px] text-text-secondary" title={item.label}>
        {item.label}
      </p>
      <p className="mt-0.5 font-display text-[18px] leading-tight font-semibold text-text tabular-nums">
        {fmt(item.test, 2)}
        <span className="ml-1 text-[11px] font-medium text-text-tertiary">test {info?.short}</span>
      </p>
      <p className="text-[11px] text-text-tertiary tabular-nums">
        CV {fmt(item.cv_mean, 2)} ± {fmt(item.cv_std, 2)}
      </p>
    </div>
  );
}

function ModelMatrix({ selected }: { selected: SelectedModelSummary[] }) {
  const rows = (["math", "portuguese"] as const).flatMap((cohort) =>
    (["regression", "classification"] as const).map((task) => ({ cohort, task })),
  );
  const find = (cohort: string, task: string, scenario: string) =>
    selected.find((s) => s.cohort === cohort && s.task === task && s.scenario === scenario);

  return (
    <>
      {/* Phones: one card per cohort and task, scenarios stacked. */}
      <ul className="space-y-3 sm:hidden" aria-label="Selected models">
        {rows.map(({ cohort, task }) => (
          <li key={`${cohort}-${task}`} className="rounded-2xl bg-surface p-4 shadow-card">
            <p className="text-[14px] font-semibold text-text">
              {cohort === "math" ? "Mathematics" : "Portuguese"}
              <span className="ml-1.5 text-[12px] font-normal text-text-secondary">
                {task === "regression" ? "Final grade · RMSE ↓" : "Academic risk · F1 ↑"}
              </span>
            </p>
            <dl className="mt-2 divide-y divide-separator">
              {scenarios.map((sc) => (
                <div key={sc} className="flex items-start justify-between gap-3 py-2">
                  <dt className="pt-0.5 text-[12px] font-medium text-text-secondary">
                    {scenarioInfo[sc].label}
                  </dt>
                  <dd className="min-w-0 text-right">
                    <ModelCell item={find(cohort, task, sc)} />
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
      <div
        tabIndex={0}
        role="region"
        aria-label="Selected models table (scrollable)"
        className="hidden overflow-x-auto rounded-2xl bg-surface shadow-card sm:block"
      >
        <table className="w-full min-w-[640px] text-left text-[13px]">
          <caption className="sr-only">
            Selected model per cohort, task and scenario with held-out test and cross-validated
            scores
          </caption>
          <thead>
            <tr className="border-b border-separator bg-surface-muted text-[11px] text-text-tertiary">
              <th scope="col" className="px-4 py-2.5 font-medium">
                Cohort · task
              </th>
              {scenarios.map((s) => (
                <th key={s} scope="col" className="px-4 py-2.5 font-medium">
                  {scenarioInfo[s].label}
                  <span className="block font-normal">{scenarioInfo[s].inputs}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-separator">
            {rows.map(({ cohort, task }) => (
              <tr key={`${cohort}-${task}`}>
                <th scope="row" className="px-4 py-3 align-top font-medium text-text">
                  {cohort === "math" ? "Mathematics" : "Portuguese"}
                  <span className="block text-[12px] font-normal text-text-secondary">
                    {task === "regression" ? "Final grade · RMSE ↓" : "Academic risk · F1 ↑"}
                  </span>
                </th>
                {scenarios.map((s) => (
                  <td key={s} className="px-4 py-3 align-top">
                    <ModelCell item={find(cohort, task, s)} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Findings({ cohort, scenario }: { cohort: string; scenario: Scenario }) {
  const research = useApi<ResearchQuestions>(cohortPath("/statistics/hypothesis-tests", cohort));
  const pipeline = useApi<PipelineSummary>(withQuery("/pipeline/summary", { cohort, scenario }));
  const rq = research.data?.cohort === cohort ? research.data : undefined;
  const pipe =
    pipeline.data?.cohort === cohort && pipeline.data.scenario === scenario
      ? pipeline.data
      : undefined;

  if (research.error)
    return <p className="px-1 text-[13px] text-text-secondary">{research.error.message}</p>;
  const pipelineError = pipeline.error?.message;

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[14px] font-semibold text-text">Research questions</h3>
          <KindBadge kind="observed" />
        </div>
        {!rq ? (
          <LoadingBlock label="Loading research questions" height="h-40" className="mt-4" />
        ) : (
          <ul className="mt-3 divide-y divide-separator">
            {rq.items.map((item) => (
              <li key={item.key} className="flex gap-3 py-2.5">
                <span className="w-9 shrink-0 pt-px font-mono text-[11px] text-text-tertiary">
                  {item.key}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] leading-[18px] text-text">{item.question}</p>
                  <p className="mt-1 text-[11px] text-text-tertiary tabular-nums">
                    {item.evidence === "confirmatory" ? "Confirmatory" : "Exploratory"} · adjusted p{" "}
                    {fmtP(item.p_adjusted)}
                    {item.effect &&
                      ` · ${item.effect.name} ${fmt(item.effect.value, 2)} (${item.effect.magnitude})`}
                  </p>
                </div>
                <StatusBadge tone={item.significant ? "accent" : "neutral"} className="mt-px">
                  {item.significant ? "Significant" : "Not significant"}
                </StatusBadge>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-[11px] leading-4 text-text-tertiary">
          Significance is after correction for multiple comparisons (
          {rq?.correction ?? "see Statistics"}). Effect size, not the p-value, indicates how large a
          difference is. Associations, not causes.
        </p>
        <Link
          href="/statistics"
          className="mt-3 inline-flex items-center gap-1 text-[13px] text-accent hover:underline"
        >
          Full statistical analysis <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </Card>

      <div className="space-y-3">
        <Card className="p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-[14px] font-semibold text-text">Strongest group differences</h3>
            <KindBadge kind="observed" />
          </div>
          {pipelineError ? (
            <p className="mt-3 text-[13px] text-text-secondary">{pipelineError}</p>
          ) : !pipe ? (
            <LoadingBlock label="Loading group highlights" height="h-20" className="mt-4" />
          ) : pipe.risk_profile_highlights.length ? (
            <ul className="mt-3 space-y-2 text-[13px] leading-[18px] text-text">
              {pipe.risk_profile_highlights.map((h) => (
                <li key={h} className="flex gap-2">
                  <span
                    className="mt-[7px] size-1 shrink-0 rounded-full bg-text-tertiary"
                    aria-hidden
                  />
                  {h}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-[13px] text-text-secondary">No group profile is available.</p>
          )}
          <Link
            href="/risk-analysis"
            className="mt-3 inline-flex items-center gap-1 text-[13px] text-accent hover:underline"
          >
            Risk profiles <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </Card>

        <Card className="p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-[14px] font-semibold text-text">What the models rely on</h3>
            <KindBadge kind="explanation" />
          </div>
          <p className="mt-1 text-[12px] text-text-secondary">
            {scenarioInfo[scenario].label} scenario · top attributes by held-out permutation
            importance
          </p>
          {pipelineError ? (
            <p className="mt-3 text-[13px] text-text-secondary">{pipelineError}</p>
          ) : !pipe ? (
            <LoadingBlock label="Loading model reliance" height="h-20" className="mt-4" />
          ) : (
            <dl className="mt-3 space-y-2.5 text-[13px]">
              {(["classification", "regression"] as const).map((task) => (
                <div key={task}>
                  <dt className="text-[11px] font-medium text-text-tertiary">
                    {task === "classification" ? "Academic-risk model" : "Final-grade model"}
                  </dt>
                  <dd className="mt-0.5 text-text">
                    {pipe.top_attributes[task]?.length
                      ? pipe.top_attributes[task].slice(0, 4).join(" · ")
                      : "Not available"}
                  </dd>
                </div>
              ))}
            </dl>
          )}
          <p className="mt-3 text-[11px] leading-4 text-text-tertiary">
            Reliance of a model, not a cause of a student&apos;s grade.
          </p>
          <Link
            href="/interpretability"
            className="mt-2 inline-flex items-center gap-1 text-[13px] text-accent hover:underline"
          >
            Interpretability <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </Card>
      </div>
    </div>
  );
}

export function DashboardView() {
  const [cohort, setCohort] = useCohort();
  const [scenario, setScenario] = useScenario();
  const [reloadKey, setReloadKey] = useState(0);
  const summary = useApi<DashboardSummary>("/dashboard/summary", reloadKey);
  const data = summary.data;
  const component = (key: string) => data?.components.find((c) => c.key === key);

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Overview"
        title={site.name}
        description="Statistics and exploratory analysis of two Portuguese secondary-school cohorts, followed by interpretable models of the final grade and of academic risk — a final grade below 10. The data contain no dropout outcome."
      >
        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-[14px]">
          <Link
            href="/about"
            className="inline-flex items-center gap-1 text-accent hover:underline"
          >
            Read the methodology
          </Link>
          <a
            href={site.dataset.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-0.5 text-accent hover:underline"
          >
            Dataset on UCI
            <ArrowUpRight className="size-3.5" aria-hidden />
          </a>
          <a
            href={site.repository}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-0.5 text-accent hover:underline"
          >
            Source on GitHub
            <ArrowUpRight className="size-3.5" aria-hidden />
          </a>
        </div>
      </PageHeader>

      {summary.error ? (
        <DataUnavailable error={summary.error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : !data ? (
        <LoadingBlock label="Loading dashboard" count={2} height="h-72" />
      ) : (
        <>
          {data.status === "degraded" && (
            <Callout tone="caution" title="Some results are unavailable">
              The API reports a degraded state. Parts that depend on missing components are omitted
              rather than estimated; see System status below for the commands that restore them.
            </Callout>
          )}

          <Section
            title="The cohorts"
            description="What happened in the historical data: observed proportions with 95% Wilson intervals, not predictions."
            action={<KindBadge kind="observed" />}
          >
            {data.dataset.available && data.dataset.cohorts.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {data.dataset.cohorts.map((o) => (
                  <CohortCard key={o.cohort} overview={o} />
                ))}
              </div>
            ) : (
              <EmptyState title="The dataset is not available">
                {data.dataset.detail}
                {component("dataset")?.action && (
                  <code className="mt-3 block rounded-lg bg-fill px-3 py-2 font-mono text-[12px] text-text">
                    {component("dataset")?.action}
                  </code>
                )}
              </EmptyState>
            )}
          </Section>

          <Section
            title="Selected models"
            description={`Scores of the model chosen by cross-validation for each cohort, task and scenario${data.models.trained_at ? ` (training run of ${fmtDate(data.models.trained_at)})` : ""}. Test = held-out students, scored once; CV = mean ± SD over five outer folds on the training set.`}
            action={<KindBadge kind="model_evaluation" />}
          >
            {data.models.available && data.models.selected.length ? (
              <>
                <ModelMatrix selected={data.models.selected} />
                <p className="mt-3 px-1 text-[12px] leading-[18px] text-text-tertiary">
                  Later scenarios use the period grades G1 and G2, which are only known part-way
                  through the year; their higher scores reflect that extra information, not a better
                  method. The early scenario is the realistic one for early support.
                </p>
                <Link
                  href="/model-comparison"
                  className="mt-2 inline-flex items-center gap-1 px-1 text-[13px] text-accent hover:underline"
                >
                  Compare every model and baseline <ArrowRight className="size-3.5" aria-hidden />
                </Link>
              </>
            ) : (
              <EmptyState title="No trained models are available">
                {data.models.detail}
                {component("models")?.action && (
                  <code className="mt-3 block rounded-lg bg-fill px-3 py-2 font-mono text-[12px] text-text">
                    {component("models")?.action}
                  </code>
                )}
              </EmptyState>
            )}
          </Section>

          {data.dataset.available && (
            <Section
              title="Key findings"
              description="Results from the statistical analysis and the selected models for one cohort."
            >
              <Toolbar className="mb-1 px-1">
                <ToolbarItem label="Cohort">
                  <SegmentedControl
                    label="Cohort"
                    options={cohortOptions}
                    value={cohort}
                    onChange={setCohort}
                  />
                </ToolbarItem>
                <ToolbarItem label="Scenario (model reliance)">
                  <SegmentedControl
                    label="Scenario"
                    options={scenarioOptions}
                    value={scenario}
                    onChange={setScenario}
                  />
                </ToolbarItem>
              </Toolbar>
              <Findings cohort={cohort} scenario={scenario} />
            </Section>
          )}

          <div className="grid gap-12 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)] xl:gap-8">
            <Section title="Explore" description="Each page reads its results from the API.">
              <GroupedList>
                {allModules.map((m) => (
                  <ListRow
                    key={m.key}
                    href={m.href}
                    leading={
                      <IconTile>
                        <m.icon className="size-4" />
                      </IconTile>
                    }
                    title={m.title}
                    description={m.summary}
                  />
                ))}
              </GroupedList>
            </Section>

            <div className="space-y-12">
              <Section
                title="System status"
                description="Read live from the backend's readiness check."
                action={
                  <StatusBadge tone={data.status === "ready" ? "positive" : "caution"}>
                    {data.status === "ready" ? "Ready" : "Degraded"}
                  </StatusBadge>
                }
              >
                <SystemStatus components={data.components} />
              </Section>

              <Section title="Reading these results">
                <Card className="p-5">
                  <ul className="space-y-2 text-[13px] leading-5 text-text-secondary">
                    {data.notes.map((n) => (
                      <li key={n} className="flex gap-2">
                        <span
                          className="mt-2 size-1 shrink-0 rounded-full bg-text-tertiary"
                          aria-hidden
                        />
                        {n}
                      </li>
                    ))}
                  </ul>
                </Card>
              </Section>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
