import type { Metadata } from "next";
import { ArrowUpRight } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { GroupedList, ListRow } from "@/components/ui/GroupedList";
import { Section } from "@/components/ui/Section";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "About & Methodology" };

const pipeline = [
  ["Data validation", "Schema, types, ranges, duplicates and cohort overlap are checked first."],
  ["Descriptive statistics", "Central tendency, dispersion, quartiles and distribution shape."],
  [
    "Relationships",
    "Pearson for approximately normal, linear relationships; Spearman for ordinal or non-normal data.",
  ],
  [
    "Inference",
    "t-test and ANOVA when assumptions hold, otherwise Mann–Whitney and Kruskal–Wallis; chi-square for categorical associations. Effect sizes reported throughout.",
  ],
  ["Exploration", "Univariate, bivariate and multivariate analysis, outliers and profiling."],
  ["Preprocessing", "Encoding, scaling and feature engineering fitted inside training folds only."],
  ["Modelling", "Candidate models compared against baselines with cross-validation."],
  [
    "Interpretation",
    "Model-agnostic explanations that turn predictions into academic-risk insight.",
  ],
] as const;

const scenarios = [
  ["Full history", "Non-grade attributes + G1 + G2", "Late-year prediction"],
  ["Mid-year", "Non-grade attributes + G1", "After the first period"],
  ["Early", "Non-grade attributes only", "Early warning, before any grade"],
] as const;

const stack = [
  ["Analytics", "Python · pandas · NumPy · SciPy · scikit-learn"],
  ["API", "FastAPI · Pydantic"],
  ["Interface", "Next.js · TypeScript · Tailwind CSS"],
] as const;

export default function AboutPage() {
  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="About & Methodology"
        title="How the analysis is designed"
        description="The contribution of this project is an integrated, reproducible workflow — not any individual technique. These are the rules every result in the system will follow."
      />

      <Section title="Research basis">
        <div className="rounded-2xl bg-surface p-5 shadow-card sm:p-6">
          <p className="text-[15px] leading-6 text-text">
            Cortez, P., &amp; Silva, A. M. G. (2008).{" "}
            <em>Using Data Mining to Predict Secondary School Student Performance.</em> Proceedings
            of the 5th Future Business Technology Conference (FUBUTEC 2008), 5–12.
          </p>
          <p className="mt-3 text-[14px] leading-[21px] text-text-secondary">
            The original study applied data-mining models to the same data and showed that prior
            period grades dominate predictive performance. This project extends the workflow with a
            statistical and exploratory foundation, multiple model comparison and interpretable
            academic-risk insight.
          </p>
        </div>
      </Section>

      <Section title="Dataset">
        <GroupedList>
          <ListRow
            title={site.dataset.name}
            description="Two Portuguese secondary-school cohorts — Mathematics and Portuguese language — with demographic, family, social, behavioural and academic attributes, and period grades G1, G2 and G3 on a 0–20 scale."
            trailing={
              <a
                href={site.dataset.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-0.5 text-[13px] text-accent hover:underline"
              >
                UCI
                <ArrowUpRight className="size-3.5" aria-hidden />
              </a>
            }
          />
        </GroupedList>
      </Section>

      <Section title="Analytical pipeline">
        <ol className="divide-y divide-separator rounded-2xl bg-surface shadow-card">
          {pipeline.map(([title, detail], index) => (
            <li key={title} className="flex gap-4 px-4 py-3.5 sm:px-5">
              <span className="w-5 pt-px font-mono text-[12px] text-text-tertiary tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="text-[14px] font-medium text-text">{title}</p>
                <p className="mt-0.5 text-[13px] leading-[19px] text-text-secondary">{detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        title="Targets and leakage control"
        description="Defined before any model is trained."
      >
        <div className="space-y-5 rounded-2xl bg-surface p-5 text-[14px] leading-[21px] shadow-card sm:p-6">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-[12px] font-medium text-text-tertiary">Regression target</dt>
              <dd className="mt-1 text-text">Final grade G3 (0–20)</dd>
            </div>
            <div>
              <dt className="text-[12px] font-medium text-text-tertiary">Classification target</dt>
              <dd className="mt-1 text-text">
                Academic risk: G3 below the pass mark of 10{" "}
                <span className="text-text-secondary">
                  (fixed in the Phase 3 preprocessing pipeline)
                </span>
              </dd>
            </div>
          </dl>
          <p className="text-text-secondary">
            G3 is never an input to a model that predicts G3 or a label derived from it. Because G1
            and G2 are only known part-way through the year, every experiment is reported under an
            explicit input scenario:
          </p>
          <div className="overflow-x-auto rounded-xl border border-separator">
            <table className="w-full min-w-[420px] text-left text-[13px]">
              <thead className="bg-surface-muted text-text-tertiary">
                <tr>
                  <th className="px-4 py-2 font-medium">Scenario</th>
                  <th className="px-4 py-2 font-medium">Inputs</th>
                  <th className="px-4 py-2 font-medium">Represents</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-separator">
                {scenarios.map(([id, inputs, represents]) => (
                  <tr key={id}>
                    <td className="px-4 py-2.5 font-semibold whitespace-nowrap text-text">{id}</td>
                    <td className="px-4 py-2.5 text-text">{inputs}</td>
                    <td className="px-4 py-2.5 text-text-secondary">{represents}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-text-secondary">
            The dataset contains no dropout outcome, so the system describes{" "}
            <span className="font-medium text-text">academic risk</span> — the risk of failing the
            final assessment — and does not claim to predict dropout.
          </p>
        </div>
      </Section>

      <Section title="Evaluation">
        <GroupedList>
          <ListRow title="Regression" description="MAE · MSE · RMSE · R²" />
          <ListRow
            title="Classification"
            description="Accuracy · Precision · Recall · F1 · ROC-AUC · Confusion matrix, always alongside a majority-class baseline"
          />
        </GroupedList>
      </Section>

      <Section title="Technology">
        <GroupedList>
          {stack.map(([layer, tools]) => (
            <ListRow key={layer} title={layer} description={tools} />
          ))}
        </GroupedList>
      </Section>
    </div>
  );
}
