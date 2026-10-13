import type { Metadata } from "next";
import { ArrowUpRight } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Callout } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "Methodology" };

// Every statement here follows docs/METHODOLOGY.md; no result is typed by hand.

const sections = [
  ["research", "Research basis"],
  ["dataset", "Dataset"],
  ["validation", "Validation and preprocessing"],
  ["statistics", "Statistics"],
  ["eda", "Exploratory analysis"],
  ["models", "Regression and classification"],
  ["evaluation", "Evaluation and selection"],
  ["scenarios", "Input scenarios"],
  ["risk", "Academic risk"],
  ["interpretability", "Interpretability"],
  ["leakage", "Leakage prevention"],
  ["limitations", "Limitations and responsible use"],
] as const;

function Block({
  id,
  title,
  children,
}: {
  id: (typeof sections)[number][0];
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 space-y-3">
      <h2 className="px-1 font-display text-[20px] font-semibold tracking-[-0.015em] text-text">
        {title}
      </h2>
      <Card className="space-y-3 p-5 text-[14px] leading-[22px] text-text-secondary sm:p-6 [&_strong]:font-medium [&_strong]:text-text">
        {children}
      </Card>
    </section>
  );
}

function Table({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <div
      tabIndex={0}
      role="region"
      aria-label={`${head.join(", ")} (scrollable table)`}
      className="overflow-x-auto rounded-xl border border-separator"
    >
      <table className="w-full min-w-[480px] text-left text-[13px]">
        <thead className="bg-surface-muted text-[11px] text-text-tertiary">
          <tr>
            {head.map((h) => (
              <th key={h} scope="col" className="px-4 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-separator">
          {rows.map((row) => (
            <tr key={row[0]}>
              {row.map((cell, i) => (
                <td
                  key={i}
                  className={i === 0 ? "px-4 py-2.5 font-medium text-text" : "px-4 py-2.5"}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function List({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2.5">
          <span className="mt-[9px] size-1 shrink-0 rounded-full bg-text-tertiary" aria-hidden />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function MethodologyPage() {
  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Project"
        title="Methodology"
        description="How the data were checked, analysed and modelled, and the rules every result follows. The contribution is an integrated, reproducible workflow — statistics, exploration, model comparison and interpretable risk analysis — not a new technique."
      />

      <nav aria-label="On this page" className="rounded-2xl bg-surface p-4 shadow-card sm:p-5">
        <p className="mb-2 px-1 text-[11px] font-semibold tracking-[0.06em] text-text-tertiary uppercase">
          On this page
        </p>
        <ol className="grid gap-x-6 gap-y-1 text-[13px] sm:grid-cols-2 lg:grid-cols-3">
          {sections.map(([id, title], index) => (
            <li key={id}>
              <a
                href={`#${id}`}
                className="flex gap-2 rounded-md px-1 py-1 text-text-secondary transition-colors hover:text-accent"
              >
                <span className="w-5 font-mono text-[11px] text-text-tertiary tabular-nums">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <Block id="research" title="Research basis">
        <p className="text-text">
          Cortez, P., &amp; Silva, A. M. G. (2008).{" "}
          <em>Using Data Mining to Predict Secondary School Student Performance.</em> Proceedings of
          the 5th Future Business Technology Conference (FUBUTEC 2008), 5–12.
        </p>
        <p>
          The paper applied data-mining models to the same data under three input configurations —
          with both period grades, with the first only, and with none — and showed that prior grades
          dominate predictive performance. This project keeps that scenario design and adds a
          statistical and exploratory foundation, a documented model comparison and interpretable
          academic-risk analysis.
        </p>
      </Block>

      <Block id="dataset" title="Dataset">
        <p>
          <strong>{site.dataset.name}</strong> (UCI Machine Learning Repository): two cohorts of
          Portuguese secondary-school students — Mathematics (395 students) and Portuguese language
          (649) — with 30 demographic, family, social and school attributes and the period grades
          G1, G2 and G3 on a 0–20 scale.{" "}
          <a
            href={site.dataset.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-0.5 text-accent hover:underline"
          >
            Dataset on UCI
            <ArrowUpRight className="size-3.5" aria-hidden />
          </a>
        </p>
        <p>
          The cohorts are analysed and modelled separately. They are different subjects with
          different grade distributions, and there is no student identifier to merge them safely;
          the Data Explorer reports only an approximate attribute-based overlap.
        </p>
      </Block>

      <Block id="validation" title="Validation and preprocessing">
        <List
          items={[
            <>
              <strong>Integrity.</strong> Each file must match a pinned SHA-256 checksum. The raw
              files are read, never modified.
            </>,
            <>
              <strong>Validation.</strong> Exactly the 33 documented columns, no missing values,
              only documented category codes, grades as integers in 0–20 and coded scales within
              their ranges. Validation reports and never deletes; both official files pass every
              check.
            </>,
            <>
              <strong>Outliers and zero grades.</strong> Values within the documented range —
              including high absence counts and G3 = 0 — are genuine data. They are flagged (Tukey
              1.5·IQR, z-scores) but never removed.
            </>,
            <>
              <strong>Encoding.</strong> Binary attributes become one indicator, nominal attributes
              are fully one-hot encoded, ordinal codes keep their documented order. Categories come
              from the data dictionary, so every split produces identical columns.
            </>,
            <>
              <strong>Engineered features.</strong> Only two: <code>has_past_failures</code> and{" "}
              <code>log_absences</code> = ln(1 + absences), both row-wise and free of grades.
            </>,
            <>
              <strong>Split.</strong> 80/20 within each cohort, stratified on academic risk, seed
              42: Mathematics 316 / 79 and Portuguese 519 / 130 students. Imputers, encoders and
              scalers are fitted inside each training fold only.
            </>,
          ]}
        />
      </Block>

      <Block id="statistics" title="Descriptive and inferential statistics">
        <List
          items={[
            "Descriptive statistics: central tendency, dispersion, quartiles and distribution shape, with confidence intervals for means.",
            "Correlation: Pearson where a relationship is approximately linear and normal, Spearman for ordinal or non-normal data, each with a confidence interval.",
            "Group comparisons: normality and equal-variance checks decide between t-test / ANOVA (Welch where variances differ) and Mann–Whitney U / Kruskal–Wallis, with post-hoc tests (Tukey HSD, Games–Howell or Dunn with Holm adjustment) for three or more groups.",
            "Categorical associations with academic risk: chi-square, or Fisher's exact test when expected counts are small.",
            "Effect sizes reported throughout: Cohen's d, η², rank-biserial r and Cramér's V.",
            "Multiple comparisons: Holm–Bonferroni across the confirmatory research questions, Benjamini–Hochberg within exploratory families.",
          ]}
        />
        <p>
          Statistical significance and effect size answer different questions: a small p-value says
          a difference is unlikely to be chance, the effect size says how large it is. A sensitivity
          analysis repeats key results without the G3 = 0 students. All findings are associations in
          observational data.
        </p>
      </Block>

      <Block id="eda" title="Exploratory data analysis">
        <p>
          Histograms and category distributions, box plots of the final grade by group, scatter
          plots with overlapping observations sized by count, a Spearman correlation heatmap and an
          academic-risk profile comparing students above and below the pass mark. Every chart has a
          data table.
        </p>
      </Block>

      <Block id="models" title="Regression and classification">
        <Table
          head={["Task", "Target", "Candidate models"]}
          rows={[
            [
              "Regression",
              "Final grade G3 (0–20)",
              "Mean baseline, linear regression, decision tree, random forest",
            ],
            [
              "Classification",
              "Academic risk: G3 < 10",
              "Majority-class baseline, logistic regression, decision tree, k-nearest neighbours, SVM (RBF), random forest",
            ],
          ]}
        />
        <p>
          Classifiers that support it use balanced class weights; there is no resampling and no
          synthetic student. Hyperparameters are tuned on bounded grids only.
        </p>
      </Block>

      <Block id="evaluation" title="Evaluation and model selection">
        <List
          items={[
            <>
              <strong>Nested cross-validation</strong> on the training set: 5 outer folds, with a
              5-fold grid search inside each. The reported CV mean ± SD estimates the whole
              procedure, tuning included.
            </>,
            <>
              <strong>Held-out test set</strong>, scored once per model after training. It is
              reported for every model but never used to choose one.
            </>,
            <>
              <strong>Selection rule:</strong> best mean CV RMSE (regression) or at-risk F1
              (classification), then the simplest model within one standard error, and a check that
              the choice beats its baseline.
            </>,
            <>
              <strong>Metrics:</strong> MAE, RMSE and R² for regression; precision, recall, F1,
              ROC-AUC, specificity and confusion matrices for classification, always beside a
              baseline. ROC-AUC is computed from scores, never from hard labels.
            </>,
          ]}
        />
      </Block>

      <Block id="scenarios" title="Input scenarios">
        <Table
          head={["Scenario", "Inputs", "When it would be available"]}
          rows={[
            ["Early", "Non-grade attributes only", "Before any grade of the year"],
            ["Mid-year", "Non-grade attributes + G1", "After the first grading period"],
            ["Full history", "Non-grade attributes + G1 + G2", "After the second grading period"],
          ]}
        />
        <p>
          Period grades correlate strongly with the final grade, so later scenarios score higher
          because they know more, not because their models are better. The early scenario is the
          realistic one for early support. Every scenario has its own selected model.
        </p>
      </Block>

      <Block id="risk" title="Academic risk">
        <p>
          <strong>Academic risk</strong> means a final grade G3 below the pass mark of 10. The
          dataset contains no dropout outcome, so the system never claims to predict dropout. On the
          observed data, 32.9% of Mathematics and 15.4% of Portuguese students were below the pass
          mark.
        </p>
        <p>
          Group profiles report observed proportions with 95% Wilson intervals for school-related
          attributes only, with a minimum group size of 10 for a reliable estimate. No low / medium
          / high bands are introduced, because no validated educational thresholds exist for them.
        </p>
      </Block>

      <Block id="interpretability" title="Interpretability">
        <List
          items={[
            "Explanations are reported per original attribute, so encoded and engineered columns of one attribute always move together.",
            "Individual explanations: interventional Shapley values estimated by permutation sampling (antithetic, seeded, exactly additive), with a standard error for each contribution.",
            "Global importance: permutation importance on the held-out test set (plus a G3 > 0 variant for regression), mean absolute Shapley value, impurity importance and coefficients — each on its own scale, never compared across methods.",
            "Probabilities are shown only where a model produces them; they come from class-weighted training and are not calibrated, so they order students rather than give a chance of failing.",
            "Sensitivity experiments vary one school-related attribute while everything else stays fixed. They describe the model's response, not what would happen if a student changed something.",
          ]}
        />
      </Block>

      <Block id="leakage" title="Target leakage prevention">
        <List
          items={[
            "G3 and the derived academic-risk label are never inputs, in any scenario; the API rejects them.",
            "G1 and G2 are rejected outside the scenarios that allow them, and each scenario's model only ever receives that scenario's columns.",
            "Preprocessing statistics are learned on training rows only, inside each cross-validation fold.",
            "The prediction form only shows the inputs of the selected scenario and never offers G3.",
          ]}
        />
      </Block>

      <Block id="limitations" title="Limitations and responsible use">
        <List
          items={[
            "Two Portuguese schools in 2005–2006: results may not transfer to other schools, years or systems.",
            "Observational, cross-sectional data: associations and model reliance are not causes.",
            "Small test sets (79 and 130 students) make test metrics, importances and calibration noisy.",
            "G3 = 0 probably sometimes means the final evaluation was not taken; it is kept and examined in sensitivity checks.",
            "Early-scenario models find only part of the students who finish below the pass mark.",
          ]}
        />
        <Callout
          tone="responsible"
          title="Responsible use"
          className="mt-2 bg-surface-muted shadow-none"
        >
          Predictions and suggestions support discussion between a student and a teacher or adviser.
          They do not determine a student&apos;s ability or future, must not be used for
          disciplinary decisions, and no demographic group is labelled as at risk.
        </Callout>
      </Block>

      <p className="px-1 text-[13px] text-text-tertiary">
        Full documentation, including every generated result, is in the{" "}
        <a
          href={site.repository}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-0.5 text-accent hover:underline"
        >
          repository
          <ArrowUpRight className="size-3.5" aria-hidden />
        </a>{" "}
        (docs/METHODOLOGY.md).
      </p>
    </div>
  );
}
