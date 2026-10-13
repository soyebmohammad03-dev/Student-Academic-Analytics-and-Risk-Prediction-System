import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Section } from "@/components/ui/Section";
import { PhaseBadge } from "@/components/ui/StatusBadge";
import type { AppModule } from "@/lib/modules";

/**
 * Honest placeholder for a module that has not been built yet: states what the
 * module will contain and when, without rendering any sample data.
 */
export function ModulePlaceholder({ module: appModule }: { module: AppModule }) {
  const Icon = appModule.icon;
  const inProgress = appModule.status === "in_progress";

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow={`${inProgress ? "In progress" : "Planned"} · Phase ${appModule.phase}`}
        title={appModule.title}
        description={appModule.summary}
      />

      <div className="flex flex-col items-center rounded-2xl bg-surface px-6 py-14 text-center shadow-card sm:py-20">
        <span className="flex size-12 items-center justify-center rounded-[14px] bg-fill text-text-secondary">
          <Icon className="size-6" strokeWidth={1.75} />
        </span>
        <h2 className="mt-5 font-display text-[17px] font-semibold tracking-[-0.01em] text-text">
          {inProgress
            ? "Results are computed; this page is not built yet"
            : "This module is not available yet"}
        </h2>
        <p className="mt-1.5 max-w-md text-[14px] leading-[21px] text-text-secondary">
          {inProgress
            ? (appModule.progressNote ??
              "Results from the real dataset are available through the API. No sample figures are shown here.")
            : `It will be populated with results computed from the real dataset in Phase ${appModule.phase}. No sample or placeholder figures are shown in the meantime.`}
        </p>
        <div className="mt-5">
          <PhaseBadge phase={appModule.phase} />
        </div>
      </div>

      <Section title="Planned scope">
        <ul className="divide-y divide-separator rounded-2xl bg-surface shadow-card">
          {appModule.scope.map((item) => (
            <li
              key={item}
              className="flex items-start gap-3 px-4 py-3 text-[14px] leading-5 text-text sm:px-5"
            >
              <span className="mt-2 size-1 shrink-0 rounded-full bg-text-tertiary" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      </Section>

      <p className="px-1 text-[13px] text-text-tertiary">
        See the{" "}
        <Link href="/about" className="text-accent hover:underline">
          methodology
        </Link>{" "}
        for how targets, features and evaluation are defined.
      </p>
    </div>
  );
}
