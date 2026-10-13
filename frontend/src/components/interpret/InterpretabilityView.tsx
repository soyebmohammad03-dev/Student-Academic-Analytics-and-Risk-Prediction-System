"use client";

import { ChevronLeft, ChevronRight, Shuffle } from "lucide-react";
import { useState } from "react";

import { DataUnavailable } from "@/components/data-explorer/states";
import { PageHeader } from "@/components/layout/PageHeader";
import { Callout, KindBadge } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { SelectControl } from "@/components/ui/Field";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import { LoadingBlock } from "@/components/ui/States";
import {
  type DatasetRecords,
  type DatasetSchema,
  type DatasetSummary,
  datasetPath,
  withQuery,
} from "@/lib/api";
import { buildFeatures, valuesFromRecord } from "@/lib/features";
import { fmt } from "@/lib/format";
import { scenarioInfo } from "@/lib/models";
import {
  type ExplainedPrediction,
  type ModelInterpretation,
  type ScenarioSensitivity,
  type Sensitivity,
  type SensitivityAttribute,
  type Task,
  scenarioOptions,
  sensitivityAttributes,
  taskOptions,
} from "@/lib/risk";
import { useApi, useApiPost } from "@/lib/useApi";
import { cohortOptions, useCohort, useScenario } from "@/lib/useCohort";

import { ExplanationChart } from "./ExplanationChart";
import { ImportanceCard } from "./ImportanceCard";
import { ScenarioSensitivityCard, SensitivityChart } from "./SensitivityChart";

function Calibration({
  calibration,
}: {
  calibration: NonNullable<ModelInterpretation["calibration"]>;
}) {
  return (
    <Card className="p-5 sm:p-6">
      <p className="text-[14px] font-semibold text-text">Probability check on the test set</p>
      <p className="mt-1 text-[13px] leading-5 text-text-secondary tabular-nums">
        Mean predicted {calibration.mean_predicted.toFixed(2)} vs observed{" "}
        {calibration.observed_rate.toFixed(2)} · Brier score {calibration.brier.toFixed(3)} · n ={" "}
        {calibration.n}
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[360px] text-[12px] tabular-nums">
          <caption className="sr-only">Predicted probability versus observed share by bin</caption>
          <thead className="text-[11px] text-text-tertiary">
            <tr>
              <th scope="col" className="py-1 text-left font-medium">
                Predicted probability
              </th>
              <th scope="col" className="py-1 text-right font-medium">
                Students
              </th>
              <th scope="col" className="py-1 text-right font-medium">
                Mean predicted
              </th>
              <th scope="col" className="py-1 text-right font-medium">
                Observed share
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-separator text-text">
            {calibration.bins.map((b) => (
              <tr key={b.low}>
                <td className="py-1.5">
                  {b.low.toFixed(1)}–{b.high.toFixed(1)}
                </td>
                <td className="py-1.5 text-right">{b.n}</td>
                <td className="py-1.5 text-right">{fmt(b.mean_predicted, 2)}</td>
                <td className="py-1.5 text-right">{fmt(b.observed_rate, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[12px] leading-[18px] text-text-secondary">{calibration.note}</p>
    </Card>
  );
}

export function InterpretabilityView() {
  const [cohort, setCohort] = useCohort();
  const [scenario, setScenario] = useScenario();
  const [task, setTask] = useState<Task>("classification");
  const [requestedRow, setRow] = useState(1);
  const [attribute, setAttribute] = useState<SensitivityAttribute>("studytime");
  const [reloadKey, setReloadKey] = useState(0);

  const importance = useApi<ModelInterpretation>(
    withQuery("/interpretability/importance", { cohort, task, scenario }),
    reloadKey,
  );
  const imp =
    importance.data?.cohort === cohort &&
    importance.data.task === task &&
    importance.data.scenario === scenario
      ? importance.data
      : undefined;

  const schema = useApi<DatasetSchema>(datasetPath("schema", cohort), reloadKey);
  const summary = useApi<DatasetSummary>(datasetPath("summary", cohort), reloadKey);
  const total = summary.data?.cohort === cohort ? summary.data.rows : undefined;
  // Cohorts differ in size: keep the row within the selected cohort.
  const row = total ? Math.min(requestedRow, total) : requestedRow;
  const records = useApi<DatasetRecords>(
    total ? datasetPath("records", cohort, { page: row, pageSize: 1 }) : null,
    reloadKey,
  );
  const columns = schema.data?.cohort === cohort ? schema.data.columns : undefined;
  const record =
    records.data?.cohort === cohort && records.data.items[0]?.row === row
      ? records.data.items[0]
      : undefined;
  const values = columns && record ? valuesFromRecord(columns, record.values) : null;
  const features = columns && values ? buildFeatures(columns, values, scenario) : null;
  const allGrades = columns && values ? buildFeatures(columns, values, "full_history") : null;

  const explained = useApiPost<ExplainedPrediction>(
    "/interpretability/explain",
    features && { cohort, task, scenario, features, top: 10 },
    reloadKey,
  );
  const sensitivity = useApiPost<Sensitivity>(
    "/interpretability/sensitivity",
    features && { cohort, task, scenario, features, attribute },
    reloadKey,
  );
  const scenarios = useApiPost<ScenarioSensitivity>(
    "/interpretability/scenario-sensitivity",
    allGrades && { cohort, task, features: allGrades },
    reloadKey,
  );

  const step = (delta: number) =>
    setRow(Math.min(Math.max(1, row + delta), total ?? Number.MAX_SAFE_INTEGER));
  const retry = () => setReloadKey((k) => k + 1);
  const attributeLabel = (name: string) => columns?.find((c) => c.name === name)?.label ?? name;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Modelling"
        title="Interpretability"
        description="Which inputs the selected models rely on, overall and for one record. These describe model behaviour on one historical dataset; high importance is not evidence that an attribute causes a grade."
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

      <Section
        title="Global importance"
        description="Each method answers a different question and has its own unit, so values are compared within a card, never across cards."
        action={<KindBadge kind="explanation" />}
      >
        {importance.error ? (
          <DataUnavailable error={importance.error} onRetry={retry} />
        ) : !imp ? (
          <LoadingBlock label="Loading feature importance" count={2} height="h-64" />
        ) : (
          <>
            <p className="mb-4 px-1 text-[14px] text-text">
              Selected model: <span className="font-semibold">{imp.model_label}</span>{" "}
              <span className="text-text-secondary">
                · {scenarioInfo[scenario].label} scenario ({scenarioInfo[scenario].inputs})
              </span>
            </p>
            <div className="grid gap-3 lg:grid-cols-2">
              {imp.methods.map((m) => (
                <ImportanceCard key={m.method_label} result={m} />
              ))}
            </div>
            {imp.calibration && (
              <div className="mt-3">
                <Calibration calibration={imp.calibration} />
              </div>
            )}
          </>
        )}
      </Section>

      <Section
        title="One record"
        description="Explain the selected model's output for one row of the cohort file, and test how the model responds when a school-related input changes."
      >
        <Card className="p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex items-center gap-1 rounded-full bg-fill p-0.5">
              <button
                type="button"
                aria-label="Previous row"
                onClick={() => step(-1)}
                disabled={row <= 1}
                className="flex size-8 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-surface hover:text-text disabled:opacity-40"
              >
                <ChevronLeft className="size-4" />
              </button>
              <span className="min-w-[7.5rem] text-center text-[13px] font-medium text-text tabular-nums">
                Row {row}
                {total ? ` of ${total}` : ""}
              </span>
              <button
                type="button"
                aria-label="Next row"
                onClick={() => step(1)}
                disabled={total !== undefined && row >= total}
                className="flex size-8 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-surface hover:text-text disabled:opacity-40"
              >
                <ChevronRight className="size-4" />
              </button>
            </div>
            {total && (
              <button
                type="button"
                onClick={() => setRow(1 + Math.floor(Math.random() * total))}
                className="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium text-accent transition-colors hover:bg-accent-soft"
              >
                <Shuffle className="size-3.5" aria-hidden />
                Random row
              </button>
            )}
            <p className="text-[12px] text-text-tertiary">
              A file position, not an identity. The record&apos;s final grade is not used.
            </p>
          </div>
        </Card>

        {records.error || schema.error || summary.error ? (
          <DataUnavailable
            error={(records.error ?? schema.error ?? summary.error)!}
            onRetry={retry}
          />
        ) : (
          <div className="space-y-3">
            {explained.error ? (
              <Callout tone="caution" title="Explanation unavailable">
                {explained.error.message}
              </Callout>
            ) : explained.data ? (
              <ExplanationChart
                explanation={explained.data.explanation}
                title={`${explained.data.prediction.model_label} · row ${row}`}
              />
            ) : (
              <LoadingBlock label="Explaining the record" height="h-72" />
            )}

            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2 px-1">
                  <label
                    htmlFor="sensitivity-attribute"
                    className="text-[12px] font-medium text-text-secondary"
                  >
                    Vary
                  </label>
                  <SelectControl
                    id="sensitivity-attribute"
                    value={attribute}
                    onChange={(event) => setAttribute(event.target.value as SensitivityAttribute)}
                    className="w-56"
                  >
                    {sensitivityAttributes.map((a) => (
                      <option key={a} value={a}>
                        {attributeLabel(a)}
                      </option>
                    ))}
                  </SelectControl>
                </div>
                {sensitivity.error ? (
                  <Callout tone="caution">{sensitivity.error.message}</Callout>
                ) : sensitivity.data ? (
                  <SensitivityChart data={sensitivity.data} />
                ) : (
                  <LoadingBlock label="Running the sensitivity experiment" height="h-56" />
                )}
              </div>
              {scenarios.error ? (
                <Callout tone="caution">{scenarios.error.message}</Callout>
              ) : scenarios.data ? (
                <ScenarioSensitivityCard data={scenarios.data} />
              ) : (
                <LoadingBlock label="Comparing scenarios" height="h-56" />
              )}
            </div>
            <Callout tone="responsible" title="Model behaviour, not causes">
              Sensitivity experiments change one input of the model while everything else stays
              fixed. They show how a model responds, not what would happen if a student changed
              something. Only school-related attributes can be varied; demographic and family
              attributes are excluded.
            </Callout>
          </div>
        )}
      </Section>
    </div>
  );
}
