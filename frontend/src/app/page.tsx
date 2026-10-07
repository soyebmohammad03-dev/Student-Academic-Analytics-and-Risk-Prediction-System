import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { SystemStatus } from "@/components/status/SystemStatus";
import { GroupedList, IconTile, ListRow } from "@/components/ui/GroupedList";
import { Section } from "@/components/ui/Section";
import { PhaseBadge, StatusBadge } from "@/components/ui/StatusBadge";
import { allModules } from "@/lib/modules";
import { site } from "@/lib/site";

const workflow = [
  { step: "Data", detail: "Validated cohorts", phase: 2 },
  { step: "Statistics", detail: "Descriptive & inferential", phase: 3 },
  { step: "Exploration", detail: "Patterns & profiles", phase: 4 },
  { step: "Preprocessing", detail: "Targets & features", phase: 5 },
  { step: "Modelling", detail: "Compare & evaluate", phase: 6 },
  { step: "Insight", detail: "Interpretable risk", phase: 7 },
];

export default function DashboardPage() {
  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="ISPA · Undergraduate AI & Data Analytics Project"
        title={site.name}
        description="Understanding student performance through statistics and exploratory analytics first, then comparing interpretable machine-learning models to identify students at academic risk."
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

      <Section
        title="Analytical workflow"
        description="Each stage builds on the one before it. Results appear here as each phase is completed."
      >
        <ol className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl bg-separator shadow-card sm:grid-cols-3 lg:grid-cols-6">
          {workflow.map(({ step, detail, phase }, index) => (
            <li key={step} className="bg-surface p-4">
              <span className="font-mono text-[11px] text-text-tertiary tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="mt-3 text-[14px] font-semibold tracking-[-0.01em] text-text">{step}</p>
              <p className="mt-0.5 text-[12px] leading-4 text-text-secondary">{detail}</p>
              <p className="mt-3 text-[11px] text-text-tertiary">Phase {phase}</p>
            </li>
          ))}
        </ol>
      </Section>

      <div className="grid gap-12 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] xl:gap-8">
        <Section
          title="Modules"
          description="Modules show results only once their phase is complete."
        >
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
                trailing={
                  m.status === "available" ? (
                    <StatusBadge tone="positive">Available</StatusBadge>
                  ) : (
                    <PhaseBadge phase={m.phase} />
                  )
                }
              />
            ))}
          </GroupedList>
        </Section>

        <div className="space-y-12">
          <Section title="System" description="Live status read from the backend.">
            <SystemStatus />
          </Section>

          <Section title="Methodological commitments">
            <div className="space-y-3 rounded-2xl bg-surface p-5 text-[14px] leading-[21px] shadow-card">
              <p className="text-text">
                <span className="font-semibold">No target leakage.</span>{" "}
                <span className="text-text-secondary">
                  The final grade G3 is never used to predict a label derived from it, and every
                  model states whether earlier grades G1/G2 were available.
                </span>
              </p>
              <p className="text-text">
                <span className="font-semibold">Academic risk, not dropout.</span>{" "}
                <span className="text-text-secondary">
                  The dataset has no dropout label, so the system predicts the risk of failing the
                  final assessment.
                </span>
              </p>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
