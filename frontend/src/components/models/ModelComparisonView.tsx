"use client";

import { useState } from "react";

import { Histogram } from "@/components/charts/Histogram";
import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { Callout, KindBadge } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { MetricCard, MetricGrid } from "@/components/ui/MetricCard";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import { LoadingBlock } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { withQuery } from "@/lib/api";
import { cn } from "@/lib/cn";
import { fmt, fmtShare } from "@/lib/format";
import {
  type CohortComparison,
  type ModelResult,
  type ScenarioComparison,
  type SelectedModelDetail,
  classificationMetrics,
  metricInfo,
  regressionMetrics,
  scenarioInfo,
} from "@/lib/models";
import { type Task, scenarioOptions, taskOptions } from "@/lib/risk";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort, useScenario } from "@/lib/useCohort";

import { ConfusionMatrix } from "./ConfusionMatrix";
import { ScenarioChart } from "./ScenarioChart";

function MetricHeader({ metric }: { metric: string }) {
  const info = metricInfo[metric];
  return (
    <span className="inline-flex items-center gap-1">
      {info?.short ?? metric}
      {info && (
        <InfoTip label={`What is ${info.label}?`}>
          <span className="font-medium text-text">{info.label}.</span> {info.definition}
        </InfoTip>
      )}
    </span>
  );
}

/** Per-fold values of one metric as dots on a 0–max strip. */
function FoldDots({ folds, max }: { folds: Array<number | null>; max: number }) {
  const defined = folds.filter((f): f is number => f !== null);
  return (
    <span
      className="relative block h-3 w-20"
      role="img"
      aria-label={`Fold values: ${defined.map((f) => f.toFixed(2)).join(", ")}`}
    >
      <span className="absolute inset-x-0 top-1/2 h-px bg-separator" aria-hidden />
      {defined.map((f, i) => (
        <span
          key={i}
          className="absolute top-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-chart-1/70"
          style={{ left: `${(100 * Math.min(Math.max(f, 0), max)) / max}%` }}
          aria-hidden
        />
      ))}
    </span>
  );
}

function Leaderboard({
  results,
  task,
  selected,
}: {
  results: ModelResult[];
  task: Task;
  selected: string | undefined;
}) {
  const metrics: readonly string[] =
    task === "regression" ? regressionMetrics : classificationMetrics;
  const primary = task === "regression" ? "rmse" : "f1";
  const lowerBetter = task === "regression";
  const foldMax =
    task === "regression"
      ? Math.ceil(
          Math.max(...results.flatMap((r) => r.cv[primary]?.folds ?? []).map((v) => v ?? 0), 1),
        )
      : 1;
  const sorted = [...results].sort((a, b) => {
    if (a.baseline !== b.baseline) return a.baseline ? 1 : -1;
    const av = a.cv[primary]?.mean ?? (lowerBetter ? Infinity : -Infinity);
    const bv = b.cv[primary]?.mean ?? (lowerBetter ? Infinity : -Infinity);
    return lowerBetter ? av - bv : bv - av;
  });
  const n = results[0];

  return (
    <div className="overflow-x-auto rounded-2xl bg-surface shadow-card">
      <table className="w-full min-w-[820px] text-left text-[13px]">
        <caption className="sr-only">
          Every candidate model and baseline: cross-validation on the training set and the held-out
          test set
        </caption>
        <thead className="text-[11px] text-text-tertiary">
          <tr className="bg-surface-muted">
            <th scope="col" rowSpan={2} className="px-4 py-2 align-bottom font-medium">
              Model
            </th>
            <th
              scope="colgroup"
              colSpan={metrics.length + 1}
              className="border-l border-separator px-4 pt-2 font-medium text-text-secondary"
            >
              Cross-validation · training set (n = {n?.n_train}), mean ± SD over 5 outer folds
            </th>
            <th
              scope="colgroup"
              colSpan={metrics.length}
              className="border-l border-separator px-4 pt-2 font-medium text-text-secondary"
            >
              Held-out test set (n = {n?.n_test}), scored once
            </th>
          </tr>
          <tr className="border-b border-separator bg-surface-muted">
            {metrics.map((m, i) => (
              <th
                key={`cv-${m}`}
                scope="col"
                className={cn(
                  "px-4 py-2 text-right font-medium whitespace-nowrap",
                  i === 0 && "border-l border-separator",
                )}
              >
                <MetricHeader metric={m} />
              </th>
            ))}
            <th scope="col" className="px-4 py-2 font-medium whitespace-nowrap">
              {metricInfo[primary].short} per fold
            </th>
            {metrics.map((m, i) => (
              <th
                key={`test-${m}`}
                scope="col"
                className={cn(
                  "px-4 py-2 text-right font-medium whitespace-nowrap",
                  i === 0 && "border-l border-separator",
                )}
              >
                <MetricHeader metric={m} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-separator">
          {sorted.map((r) => {
            const isSelected = r.model === selected;
            return (
              <tr key={r.model} className={cn(isSelected && "bg-accent-soft/60")}>
                <th scope="row" className="min-w-[13rem] px-4 py-2.5 font-medium text-text">
                  <span className="flex flex-wrap items-center gap-1.5">
                    {r.label}
                    {isSelected && <StatusBadge tone="accent">Selected</StatusBadge>}
                    {r.baseline && <StatusBadge>Baseline</StatusBadge>}
                  </span>
                  {r.diagnostics.some((d) => d.level === "warning") && (
                    <span className="mt-0.5 block text-[11px] font-normal text-caution">
                      {r.diagnostics.find((d) => d.level === "warning")?.message}
                    </span>
                  )}
                </th>
                {metrics.map((m, i) => {
                  const s = r.cv[m];
                  return (
                    <td
                      key={`cv-${m}`}
                      className={cn(
                        "px-4 py-2.5 text-right whitespace-nowrap text-text tabular-nums",
                        i === 0 && "border-l border-separator",
                      )}
                    >
                      {s?.mean === null || s?.mean === undefined ? (
                        <span
                          className="text-text-tertiary"
                          title="Undefined in every fold (e.g. precision when no student is flagged)"
                        >
                          undefined
                        </span>
                      ) : (
                        <>
                          {fmt(s.mean, 3)}
                          <span className="text-text-tertiary"> ± {fmt(s.std, 3)}</span>
                        </>
                      )}
                    </td>
                  );
                })}
                <td className="px-4 py-2.5">
                  <FoldDots folds={r.cv[primary]?.folds ?? []} max={foldMax} />
                </td>
                {metrics.map((m, i) => (
                  <td
                    key={`test-${m}`}
                    className={cn(
                      "px-4 py-2.5 text-right whitespace-nowrap text-text tabular-nums",
                      i === 0 && "border-l border-separator",
                    )}
                  >
                    {fmt(r.test[m] ?? null, 3)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SelectionCard({ detail }: { detail: SelectedModelDetail }) {
  const { selection, metadata } = detail;
  const info = metricInfo[selection.primary_metric];
  return (
    <Card className="p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-[17px] font-semibold tracking-[-0.01em] text-text">
          {selection.label}
        </h3>
        <StatusBadge tone={selection.beats_baseline ? "positive" : "caution"}>
          {selection.beats_baseline ? "Beats the baseline in CV" : "Does not beat the baseline"}
        </StatusBadge>
      </div>
      <p className="mt-2 text-[14px] leading-[21px] text-text">{selection.reason}</p>
      <dl className="mt-4 grid gap-x-6 gap-y-3 text-[12px] sm:grid-cols-2">
        <div>
          <dt className="text-text-tertiary">Rule</dt>
          <dd className="mt-0.5 text-text-secondary">
            Best mean CV {info?.short}, then the simplest model within one standard error (±
            {fmt(selection.tolerance, 3)}). The test set is not used.
          </dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Baseline CV {info?.short}</dt>
          <dd className="mt-0.5 text-text-secondary tabular-nums">
            {fmt(selection.baseline_mean, 3)}
          </dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Hyperparameters (inner grid search)</dt>
          <dd className="mt-0.5 font-mono text-[11px] break-words text-text-secondary">
            {Object.keys(metadata.best_params).length
              ? Object.entries(metadata.best_params)
                  .map(([k, v]) => `${k}=${String(v)}`)
                  .join(", ")
              : "none (fitted without tuning)"}
          </dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Inputs</dt>
          <dd className="mt-0.5 text-text-secondary">
            {metadata.feature_columns.length} columns · {scenarioInfo[metadata.scenario].inputs}
          </dd>
        </div>
      </dl>
    </Card>
  );
}

function ClassificationDetail({ detail }: { detail: SelectedModelDetail }) {
  const errors = detail.classification_errors;
  if (!errors) return null;
  const { confusion } = errors;
  const atRisk = confusion.tp + confusion.fn;
  const recall = atRisk ? confusion.tp / atRisk : null;
  return (
    <div className="space-y-3">
      {recall !== null && recall < 0.7 && (
        <Callout tone="caution" title="Limited recall">
          On the held-out test set this model flagged {confusion.tp} of the {atRisk} students who
          finished below the pass mark ({fmtShare(recall)}); {confusion.fn} were missed. A model
          like this cannot be relied on to find every student who may need support.
        </Callout>
      )}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="p-5">
          <ConfusionMatrix
            confusion={confusion}
            caption={`Held-out test set, n = ${errors.n}. Decision rule: ${errors.score_kind === "probability" ? `probability ≥ ${errors.threshold}` : `decision score ≥ ${errors.threshold}`} (not tuned).`}
          />
        </Card>
        <Card className="p-5">
          <p className="text-[14px] font-semibold text-text">What the errors look like</p>
          <ul className="mt-2 space-y-2 text-[13px] leading-[19px] text-text-secondary">
            {errors.patterns.map((p) => (
              <li key={p} className="flex gap-2">
                <span className="mt-2 size-1 shrink-0 rounded-full bg-text-tertiary" aria-hidden />
                {p}
              </li>
            ))}
          </ul>
          {errors.false_negative_grades.length > 0 && (
            <p className="mt-3 text-[12px] text-text-tertiary tabular-nums">
              Final grades of missed students:{" "}
              {errors.false_negative_grades.map((g) => `${g.grade} (×${g.count})`).join(", ")}
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

function RegressionDetail({ detail }: { detail: SelectedModelDetail }) {
  const errors = detail.regression_errors;
  if (!errors) return null;
  const zero = detail.zero_grade_sensitivity;
  return (
    <div className="space-y-3">
      <MetricGrid className="sm:grid-cols-4" label="Test-set residuals">
        <MetricCard
          label="Within ±1 grade"
          value={fmtShare(errors.residuals.within_1)}
          hint={`n = ${errors.n}`}
        />
        <MetricCard label="Within ±2 grades" value={fmtShare(errors.residuals.within_2)} />
        <MetricCard
          label="Mean residual"
          value={fmt(errors.residuals.mean, 2)}
          info="Actual − predicted. Positive means the model under-predicts on average."
        />
        <MetricCard
          label="Largest miss"
          value={fmt(
            Math.max(Math.abs(errors.residuals.min ?? 0), Math.abs(errors.residuals.max ?? 0)),
            1,
          )}
          unit="points"
        />
      </MetricGrid>
      <div className="grid gap-3 lg:grid-cols-2">
        <Histogram
          data={{
            variable: "residual",
            label: "Residuals on the test set (actual − predicted)",
            n: errors.n,
            bins: errors.histogram,
          }}
          subtitle={`Grade points, n = ${errors.n}`}
        />
        <Card className="p-5">
          <p className="text-[14px] font-semibold text-text">Error by final-grade band</p>
          <table className="mt-2 w-full text-[13px] tabular-nums">
            <thead className="text-[11px] text-text-tertiary">
              <tr>
                <th scope="col" className="py-1 text-left font-medium">
                  Band
                </th>
                <th scope="col" className="py-1 text-right font-medium">
                  n
                </th>
                <th scope="col" className="py-1 text-right font-medium">
                  MAE
                </th>
                <th scope="col" className="py-1 text-right font-medium">
                  Mean residual
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-separator text-text">
              {errors.by_band.map((b) => (
                <tr key={b.band}>
                  <td className="py-1.5">{b.band}</td>
                  <td className="py-1.5 text-right">{b.n}</td>
                  <td className="py-1.5 text-right">{fmt(b.mae, 2)}</td>
                  <td className="py-1.5 text-right">{fmt(b.mean_residual, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="mt-3 space-y-1.5 text-[12px] leading-[18px] text-text-secondary">
            {errors.patterns.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </Card>
      </div>
      {zero && (
        <Card className="p-5 text-[13px]">
          <p className="font-semibold text-text">Exploratory check: students with G3 = 0</p>
          <p className="mt-1 text-text-secondary">{zero.note}</p>
          <p className="mt-2 text-text tabular-nums">
            RMSE on {zero.test_n} test students with G3 &gt; 0: {fmt(zero.all_rows_model.rmse, 2)}{" "}
            (trained on all students) vs {fmt(zero.without_zeros_model.rmse, 2)} (retrained without
            the {zero.train_zeros_removed} training students with G3 = 0).
          </p>
        </Card>
      )}
    </div>
  );
}

function CohortTable({ data }: { data: CohortComparison }) {
  return (
    <Card className="p-5 sm:p-6">
      <div className="grid gap-4 sm:grid-cols-2">
        {data.cohorts.map((c) => (
          <div key={c.cohort}>
            <p className="text-[14px] font-semibold text-text">{c.subject}</p>
            <p className="text-[12px] text-text-secondary tabular-nums">
              {c.n} students · {c.n_train} training / {c.n_test} test ·{" "}
              {c.risk.all.at_risk_percent.toFixed(1)}% below the pass mark
            </p>
          </div>
        ))}
      </div>
      <ul className="mt-4 space-y-1.5 border-t border-separator pt-3 text-[13px] leading-[19px] text-text-secondary">
        {data.differences.map((d) => (
          <li key={d}>{d}</li>
        ))}
      </ul>
    </Card>
  );
}

export function ModelComparisonView() {
  const [cohort, setCohort] = useCohort();
  const [scenario, setScenario] = useScenario();
  const [task, setTask] = useState<Task>("classification");
  const [reloadKey, setReloadKey] = useState(0);

  const evaluations = useApi<ModelResult[]>(
    withQuery("/models/evaluations", { cohort, task, scenario }),
    reloadKey,
  );
  const selected = useApi<SelectedModelDetail>(
    withQuery("/models/selected", { cohort, task, scenario }),
    reloadKey,
  );
  const scenarios = useApi<ScenarioComparison>(
    withQuery("/models/scenario-comparison", { cohort, task }),
    reloadKey,
  );
  const cohorts = useApi<CohortComparison>("/models/cohort-comparison", reloadKey);

  const matches = (d: { cohort: string; task: string; scenario: string } | undefined) =>
    d?.cohort === cohort && d.task === task && d.scenario === scenario;
  const results =
    evaluations.data?.length && matches(evaluations.data[0]) ? evaluations.data : undefined;
  const detail = matches(selected.data?.metadata) ? selected.data : undefined;
  const scen =
    scenarios.data?.cohort === cohort && scenarios.data.task === task ? scenarios.data : undefined;
  const error = evaluations.error ?? selected.error ?? scenarios.error;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Modelling"
        title="Model Comparison"
        description="Every candidate model against a simple baseline, under each input scenario. Models are chosen by cross-validation on the training set; the held-out test set is reported but never used for the choice."
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
          <ToolbarItem label="Task">
            <SegmentedControl label="Task" options={taskOptions} value={task} onChange={setTask} />
          </ToolbarItem>
          <ToolbarItem label="Scenario">
            <SegmentedControl
              label="Scenario"
              options={scenarioOptions}
              value={scenario}
              onChange={setScenario}
            />
          </ToolbarItem>
        </Toolbar>
      </PageHeader>

      {error ? (
        <DataUnavailable error={error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : (
        <>
          <Section
            title="Across scenarios"
            description={
              scen?.note ??
              "What each scenario's selected model achieves with the information it has."
            }
            action={<KindBadge kind="model_evaluation" />}
          >
            {scen ? (
              <ScenarioChart data={scen} />
            ) : (
              <LoadingBlock label="Loading scenario comparison" />
            )}
          </Section>

          <Section
            title={`All models · ${scenarioInfo[scenario].label} scenario`}
            description={`${scenarioInfo[scenario].inputs} — ${scenarioInfo[scenario].when.toLowerCase()}. Baselines are listed last.`}
          >
            {results ? (
              <Leaderboard results={results} task={task} selected={detail?.selection.model} />
            ) : (
              <LoadingBlock label="Loading model results" height="h-64" />
            )}
          </Section>

          <Section
            title="Why this model was selected"
            description="The selection rule is applied to cross-validation results only."
          >
            {detail ? (
              <SelectionCard detail={detail} />
            ) : (
              <LoadingBlock label="Loading selection" height="h-40" />
            )}
          </Section>

          <Section
            title="Error analysis of the selected model"
            description="Held-out test set. Small test sets (79 and 130 students) make these figures noisy."
          >
            {!detail ? (
              <LoadingBlock label="Loading error analysis" height="h-56" />
            ) : task === "classification" ? (
              <ClassificationDetail detail={detail} />
            ) : (
              <RegressionDetail detail={detail} />
            )}
          </Section>

          <Section title="Cohorts compared" description="Each cohort is modelled separately.">
            {cohorts.error ? (
              <p className="px-1 text-[13px] text-text-secondary">{cohorts.error.message}</p>
            ) : cohorts.data ? (
              <CohortTable data={cohorts.data} />
            ) : (
              <LoadingBlock label="Loading cohort comparison" height="h-32" />
            )}
          </Section>

          <Section title="Metric definitions">
            <Card className="p-5 sm:p-6">
              <dl className="grid gap-x-8 gap-y-3 text-[13px] sm:grid-cols-2">
                {(task === "regression"
                  ? ["mae", "rmse", "r2"]
                  : ["precision", "recall", "f1", "roc_auc", "specificity", "accuracy"]
                ).map((m) => (
                  <div key={m}>
                    <dt className="font-medium text-text">{metricInfo[m].label}</dt>
                    <dd className="mt-0.5 leading-[19px] text-text-secondary">
                      {metricInfo[m].definition}
                    </dd>
                  </div>
                ))}
              </dl>
            </Card>
          </Section>
        </>
      )}
    </div>
  );
}
