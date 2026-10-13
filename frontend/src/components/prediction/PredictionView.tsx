"use client";

import { Eraser } from "lucide-react";
import { useRef, useState } from "react";

import { DataUnavailable } from "@/components/data-explorer/states";
import { ExplanationChart } from "@/components/interpret/ExplanationChart";
import { PageHeader } from "@/components/layout/PageHeader";
import { Callout, KindBadge } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import { LoadingBlock } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { type DatasetSchema, type DatasetSummary, datasetPath } from "@/lib/api";
import {
  type FormErrors,
  type FormValues,
  buildFeatures,
  inputColumns,
  validateRecord,
  valuesFromRecord,
} from "@/lib/features";
import { fmt, fmtInterval, fmtShare } from "@/lib/format";
import {
  type Features,
  type PredictionRequest,
  type PredictionResult,
  scenarioInfo,
} from "@/lib/models";
import {
  type ExplainedPrediction,
  type RiskInsights,
  type Scenario,
  scenarioOptions,
} from "@/lib/risk";
import { type PostState, useApi, usePost } from "@/lib/useApi";
import { cohortOptions, useCohort, useScenario } from "@/lib/useCohort";

import { RecordForm, groupColumns } from "./RecordForm";
import { RecordPicker } from "./RecordPicker";

type Submitted = { cohort: string; scenario: Scenario; features: Features };

function Pending({ state, label }: { state: PostState<unknown>; label: string }) {
  if (state.status === "loading") return <LoadingBlock label={label} height="h-40" />;
  if (state.status === "error")
    return (
      <Callout tone="caution" title="Not available">
        {state.error.message}
      </Callout>
    );
  return null;
}

function GradeCard({ result }: { result: PredictionResult }) {
  return (
    <Card className="flex flex-col p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[14px] font-semibold text-text">Predicted final grade</h3>
        <KindBadge kind="prediction" />
      </div>
      <p className="mt-4 font-display text-[44px] leading-none font-semibold tracking-[-0.03em] text-text tabular-nums">
        {fmt(result.predicted_grade, 1)}
        <span className="ml-1.5 text-[17px] font-medium tracking-normal text-text-tertiary">
          / 20
        </span>
      </p>
      <p className="mt-3 text-[13px] leading-5 text-text-secondary">
        On held-out students this model&apos;s predictions were off by{" "}
        <span className="font-medium text-text tabular-nums">
          {fmt(result.model_test_metrics.mae, 1)} grade points
        </span>{" "}
        on average (MAE; RMSE {fmt(result.model_test_metrics.rmse, 1)}), so read this as a rough
        estimate.
      </p>
      <ModelLine result={result} />
    </Card>
  );
}

function RiskCard({ result, percentile }: { result: PredictionResult; percentile: number | null }) {
  const flagged = result.at_risk === true;
  return (
    <Card className="flex flex-col p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[14px] font-semibold text-text">Academic-risk classification</h3>
        <KindBadge kind="prediction" />
      </div>
      <p className="mt-4 font-display text-[26px] leading-tight font-semibold tracking-[-0.02em] text-text">
        {flagged ? "Flagged: final grade below 10 predicted" : "Not flagged"}
      </p>
      <dl className="mt-3 space-y-1.5 text-[13px] leading-5 text-text-secondary">
        {result.probability !== null ? (
          <div className="flex flex-wrap items-center gap-1">
            <dt className="inline-flex items-center gap-1">
              Model probability
              <InfoTip label="About this probability">
                The model was trained with balanced class weights, so this score orders students by
                estimated risk but is not a calibrated chance of falling below the pass mark.
              </InfoTip>
            </dt>
            <dd className="font-medium text-text tabular-nums">{fmt(result.probability, 2)}</dd>
            <dd className="w-full text-[12px] text-text-tertiary">
              Flag when ≥ {result.threshold}; class-weighted, not calibrated.
            </dd>
          </div>
        ) : (
          <div>
            <dt className="inline">No probability is available. </dt>
            <dd className="inline">
              This model outputs a decision score ({fmt(result.score, 2)}; flagged when ≥{" "}
              {fmt(result.threshold, 0)}), which is not a probability.
            </dd>
          </div>
        )}
        {percentile !== null && (
          <div>
            <dt className="inline">Score percentile among training students: </dt>
            <dd className="inline font-medium text-text tabular-nums">
              {percentile.toFixed(0)}
              <span className="font-normal text-text-tertiary">
                {" "}
                (context, not a risk category)
              </span>
            </dd>
          </div>
        )}
      </dl>
      <p className="mt-3 text-[13px] leading-5 text-text-secondary">
        On held-out students this model found{" "}
        <span className="font-medium text-text">{fmtShare(result.model_test_metrics.recall)}</span>{" "}
        of those below the pass mark (recall); {fmtShare(result.model_test_metrics.precision)} of
        the students it flagged were below it (precision).
      </p>
      <ModelLine result={result} />
    </Card>
  );
}

function ModelLine({ result }: { result: PredictionResult }) {
  return (
    <div className="mt-auto pt-4">
      <p className="border-t border-separator pt-3 text-[12px] text-text-tertiary">
        {result.model_label} · {scenarioInfo[result.scenario].label} scenario ·{" "}
        {result.cohort === "math" ? "Mathematics" : "Portuguese"} cohort
      </p>
    </div>
  );
}

function Insights({ insights }: { insights: RiskInsights }) {
  const { group, suggestions } = insights;
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[14px] font-semibold text-text">Students with the same values</h3>
          <KindBadge kind="observed" />
        </div>
        <p className="mt-1 text-[12px] text-text-secondary">
          Observed share below the pass mark among cohort students who share each value, with 95%
          intervals. Describes groups, not this record.
        </p>
        <ul className="mt-3 divide-y divide-separator text-[13px]">
          {group.map((g) => (
            <li key={g.variable} className="flex items-baseline justify-between gap-3 py-2">
              <span className="min-w-0 text-text-secondary">
                {g.label}: <span className="text-text">{g.group}</span>
                {!g.reliable && <span className="text-caution"> · fewer than 10 students</span>}
              </span>
              <span className="shrink-0 text-right text-text tabular-nums">
                {g.risk_percent.toFixed(0)}%
                <span className="block text-[11px] text-text-tertiary">
                  n = {g.n} · {fmtInterval(g.risk_ci)}
                </span>
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[11px] text-text-tertiary tabular-nums">
          Cohort rate: {group[0]?.cohort_risk_percent.toFixed(1)}%
        </p>
      </Card>
      <Card className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[14px] font-semibold text-text">Suggestions for human review</h3>
          <StatusBadge>General, evidence-checked</StatusBadge>
        </div>
        {suggestions.suggestions.length ? (
          <ul className="mt-3 space-y-3">
            {suggestions.suggestions.map((s) => (
              <li key={s.key} className="text-[13px] leading-5">
                <p className="text-text">{s.text}</p>
                <p className="mt-0.5 text-[12px] text-text-tertiary">
                  Why: {s.trigger} {s.evidence.summary}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[13px] text-text-secondary">
            No suggestion applies to this record.
          </p>
        )}
        {suggestions.not_shown.length > 0 && (
          <details className="mt-3 text-[12px] text-text-secondary">
            <summary className="cursor-pointer select-none hover:text-text">
              {suggestions.not_shown.length} not shown: the cohort&apos;s data did not support them
            </summary>
            <ul className="mt-2 space-y-1.5">
              {suggestions.not_shown.map((s) => (
                <li key={s.key}>{s.evidence.summary}</li>
              ))}
            </ul>
          </details>
        )}
        <p className="mt-4 border-t border-separator pt-3 text-[11px] leading-4 text-text-tertiary">
          {suggestions.disclaimer}
        </p>
      </Card>
    </div>
  );
}

export function PredictionView() {
  const [cohort, setCohort] = useCohort();
  const [scenario, setScenario] = useScenario();
  const [values, setValues] = useState<FormValues>({});
  const [errors, setErrors] = useState<FormErrors>({});
  const [loadedRow, setLoadedRow] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState<Submitted | null>(null);
  const [explainTask, setExplainTask] = useState<"classification" | "regression">("classification");
  const [reloadKey, setReloadKey] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);

  const schema = useApi<DatasetSchema>(datasetPath("schema", cohort), reloadKey);
  const summary = useApi<DatasetSummary>(datasetPath("summary", cohort), reloadKey);
  const columns = schema.data?.cohort === cohort ? schema.data.columns : undefined;

  const [grade, predictGrade, resetGrade] = usePost<PredictionRequest, PredictionResult>(
    "/models/predict",
  );
  const [risk, predictRisk, resetRisk] = usePost<PredictionRequest, PredictionResult>(
    "/models/predict",
  );
  const [gradeExplained, explainGrade, resetGradeExplained] = usePost<
    PredictionRequest & { top: number },
    ExplainedPrediction
  >("/interpretability/explain");
  const [insights, getInsights, resetInsights] = usePost<
    Omit<PredictionRequest, "task">,
    RiskInsights
  >("/risk/insights");

  function clearResults() {
    resetGrade();
    resetRisk();
    resetGradeExplained();
    resetInsights();
    setSubmitted(null);
  }

  function changeCohort(next: typeof cohort) {
    clearResults();
    setLoadedRow(null);
    setCohort(next);
  }

  function changeScenario(next: Scenario) {
    clearResults();
    setErrors({});
    setScenario(next);
  }

  function onChange(name: string, value: string) {
    setValues((v) => ({ ...v, [name]: value }));
    setErrors((e) => {
      if (!e[name]) return e;
      const { [name]: _removed, ...rest } = e;
      void _removed;
      return rest;
    });
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!columns) return;
    const found = validateRecord(columns, values, scenario);
    setErrors(found);
    if (Object.keys(found).length) {
      // Focus the first invalid field in the order it appears on screen.
      const first = groupColumns(inputColumns(columns, scenario))
        .flatMap((g) => g.columns)
        .find((c) => found[c.name]);
      if (first) formRef.current?.querySelector<HTMLElement>(`#field-${first.name}`)?.focus();
      return;
    }
    const features = buildFeatures(columns, values, scenario);
    const base = { cohort, scenario, features };
    setSubmitted(base);
    predictGrade({ ...base, task: "regression" });
    predictRisk({ ...base, task: "classification" });
    explainGrade({ ...base, task: "regression", top: 10 });
    getInsights({ ...base });
  }

  const currentFeatures = columns ? buildFeatures(columns, values, scenario) : null;
  const stale =
    submitted !== null &&
    currentFeatures !== null &&
    JSON.stringify(currentFeatures) !== JSON.stringify(submitted.features);
  const visible = columns ? inputColumns(columns, scenario) : [];
  const errorCount = Object.keys(errors).length;
  const riskExplained = insights.status === "success" ? insights.data.individual : null;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Modelling"
        title="Prediction"
        description="Estimate the final grade and the academic-risk flag for one student record, using the model selected for the chosen cohort and scenario."
      >
        <Toolbar className="mt-6">
          <ToolbarItem label="Cohort">
            <SegmentedControl
              label="Cohort"
              options={cohortOptions}
              value={cohort}
              onChange={changeCohort}
            />
          </ToolbarItem>
          <ToolbarItem label="Scenario">
            <SegmentedControl
              label="Scenario"
              options={scenarioOptions}
              value={scenario}
              onChange={changeScenario}
            />
          </ToolbarItem>
        </Toolbar>
        <p className="mt-3 text-[13px] text-text-secondary">
          <span className="font-medium text-text">{scenarioInfo[scenario].label}:</span>{" "}
          {scenarioInfo[scenario].inputs} — {scenarioInfo[scenario].when.toLowerCase()}. The final
          grade G3 is the outcome and is never an input.
        </p>
      </PageHeader>

      <Callout tone="responsible" title="For educational analysis only">
        Predictions come from models trained on two Portuguese schools in 2005–2006. They support
        discussion and analysis; they do not determine a student&apos;s ability or future, and are
        not a basis for decisions on their own. Academic risk means a final grade below 10, not
        dropout.
      </Callout>

      {schema.error ? (
        <DataUnavailable error={schema.error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : !columns ? (
        <LoadingBlock label="Loading the input form" height="h-96" />
      ) : (
        <form ref={formRef} noValidate onSubmit={onSubmit} aria-label="Student record">
          <Card className="p-5 sm:p-6">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-separator pb-5">
              <RecordPicker
                cohort={cohort}
                total={summary.data?.cohort === cohort ? summary.data.rows : undefined}
                onLoad={(row, record) => {
                  setValues(valuesFromRecord(columns, record));
                  setErrors({});
                  setLoadedRow(row);
                }}
              />
              <button
                type="button"
                onClick={() => {
                  setValues({});
                  setErrors({});
                  setLoadedRow(null);
                  clearResults();
                }}
                className="inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium text-text-secondary transition-colors hover:bg-fill hover:text-text"
              >
                <Eraser className="size-3.5" aria-hidden />
                Clear form
              </button>
            </div>
            {loadedRow !== null && (
              <p className="-mt-2 mb-5 text-[12px] text-text-tertiary">
                Filled from row {loadedRow} of the{" "}
                {cohort === "math" ? "Mathematics" : "Portuguese"} file (a file position, not an
                identity). Its final grade is not loaded. Edit any value to explore.
              </p>
            )}
            <RecordForm columns={visible} values={values} errors={errors} onChange={onChange} />
            <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-separator pt-5">
              <button
                type="submit"
                className="h-10 rounded-full bg-accent-fill px-6 text-[14px] font-medium text-white transition-opacity hover:opacity-90"
              >
                Predict
              </button>
              <p className="text-[12px] text-text-tertiary" aria-live="polite">
                {errorCount
                  ? `${errorCount} field${errorCount === 1 ? " needs" : "s need"} attention.`
                  : `${visible.length} inputs for the ${scenarioInfo[scenario].label.toLowerCase()} scenario.`}
              </p>
            </div>
          </Card>
        </form>
      )}

      {submitted && (
        <div className="space-y-12 sm:space-y-14" aria-live="polite">
          {stale && (
            <Callout tone="caution" title="Inputs changed">
              The results below are for the previous submission. Press Predict to update them.
            </Callout>
          )}
          <Section
            title="Results"
            description="The two tasks use different models and are shown separately; a low predicted grade and the risk flag can disagree."
          >
            <div className="grid gap-3 md:grid-cols-2">
              {grade.status === "success" ? (
                <GradeCard result={grade.data} />
              ) : (
                <Pending state={grade} label="Predicting the final grade" />
              )}
              {risk.status === "success" ? (
                <RiskCard result={risk.data} percentile={riskExplained?.score_percentile ?? null} />
              ) : (
                <Pending state={risk} label="Classifying academic risk" />
              )}
            </div>
            {risk.status === "success" && (
              <details className="mt-3 px-1 text-[12px] text-text-secondary">
                <summary className="cursor-pointer select-none hover:text-text">
                  Caveats from the API
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-4 leading-[18px]">
                  {[
                    ...new Set([
                      ...(risk.data.caveats ?? []),
                      ...(grade.status === "success" ? grade.data.caveats : []),
                    ]),
                  ].map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </details>
            )}
          </Section>

          <Section
            title="How the models arrived at these outputs"
            description="Shapley contributions per attribute, relative to the average output over training students. They describe the model, not the reasons for a real student's grade."
          >
            <SegmentedControl
              label="Explained model"
              className="mb-4"
              options={[
                { value: "classification", label: "Academic-risk model" },
                { value: "regression", label: "Final-grade model" },
              ]}
              value={explainTask}
              onChange={setExplainTask}
            />
            {explainTask === "classification" ? (
              riskExplained ? (
                <ExplanationChart
                  explanation={riskExplained.explanation}
                  title={`${riskExplained.prediction.model_label} · academic risk`}
                />
              ) : (
                <Pending state={insights} label="Explaining the academic-risk model" />
              )
            ) : gradeExplained.status === "success" ? (
              <ExplanationChart
                explanation={gradeExplained.data.explanation}
                title={`${gradeExplained.data.prediction.model_label} · final grade`}
              />
            ) : (
              <Pending state={gradeExplained} label="Explaining the final-grade model" />
            )}
          </Section>

          <Section
            title="Context and suggestions"
            description="Observed group statistics and general suggestions are kept apart from the model outputs above."
          >
            {insights.status === "success" ? (
              <Insights insights={insights.data} />
            ) : (
              <Pending state={insights} label="Loading group statistics and suggestions" />
            )}
          </Section>
        </div>
      )}
    </div>
  );
}
