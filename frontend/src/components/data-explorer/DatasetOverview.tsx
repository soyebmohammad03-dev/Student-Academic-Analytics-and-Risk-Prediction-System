import { ArrowUpRight } from "lucide-react";

import { MetricCard as Figure } from "@/components/ui/MetricCard";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import type { DatasetSummary } from "@/lib/api";

export function DatasetOverview({ summary }: { summary?: DatasetSummary }) {
  if (!summary) {
    return (
      <Card className="space-y-5 p-5 sm:p-6" aria-busy="true" aria-label="Loading overview">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-72" />
        <Skeleton className="h-20 w-full" />
      </Card>
    );
  }

  const { target } = summary;
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 p-5 sm:p-6">
        <div>
          <h3 className="font-display text-[19px] font-semibold tracking-[-0.015em] text-text">
            {summary.subject}
          </h3>
          <p className="mt-1 text-[13px] text-text-secondary">
            <span className="font-mono text-[12px]">{summary.filename}</span> ·{" "}
            {summary.source.name}
            {" · "}
            {summary.source.license}
          </p>
        </div>
        <a
          href={summary.source.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-0.5 text-[13px] text-accent hover:underline"
        >
          Source
          <ArrowUpRight className="size-3.5" aria-hidden />
        </a>
      </div>

      <dl className="grid grid-cols-2 gap-px border-y border-separator bg-separator sm:grid-cols-4">
        <Figure label="Students" value={summary.rows} hint="rows in the file" />
        <Figure label="Attributes" value={summary.columns} hint="columns per student" />
        <Figure label="Numerical" value={summary.numerical_columns} hint="counts, scales, grades" />
        <Figure
          label="Categorical"
          value={summary.categorical_columns}
          hint="yes/no and categories"
        />
      </dl>

      <p className="px-5 py-4 text-[13px] leading-5 text-text-secondary sm:px-6">
        <span className="font-medium text-text">Performance target:</span>{" "}
        <span className="font-mono text-[12px] text-text">{target.name}</span> —{" "}
        {target.label.toLowerCase()}, {target.minimum}–{target.maximum} scale, pass mark{" "}
        {target.pass_mark}. Earlier grades{" "}
        {target.prior_grades.map((g, i) => (
          <span key={g}>
            {i > 0 && " and "}
            <span className="font-mono text-[12px] text-text">{g}</span>
          </span>
        ))}{" "}
        are recorded during the year.
      </p>
    </Card>
  );
}
