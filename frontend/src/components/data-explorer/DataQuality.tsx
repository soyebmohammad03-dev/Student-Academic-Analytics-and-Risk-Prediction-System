import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusIcon } from "@/components/ui/StatusIcon";
import type { DatasetQuality } from "@/lib/api";
import { cn } from "@/lib/cn";

function verdict(quality: DatasetQuality) {
  const failed = quality.checks.filter((c) => c.status === "fail").length;
  const warned = quality.checks.filter((c) => c.status === "warning").length;
  const total = quality.checks.length;
  if (failed)
    return {
      title: `${failed} of ${total} checks found problems`,
      body: "Some values do not match the dataset documentation. They are listed below and have not been removed.",
    };
  if (warned)
    return {
      title: `${warned} of ${total} checks need a closer look`,
      body: "Nothing is invalid, but some findings are worth reviewing before analysis.",
    };
  return {
    title: `All ${total} checks passed`,
    body: "Every value is present and matches what the dataset documentation allows.",
  };
}

function Measure({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="bg-surface px-5 py-3.5">
      <dt className="flex items-center gap-1.5 text-[12px] font-medium text-text-secondary">
        {ok !== undefined && (
          <span
            aria-hidden
            className={cn("size-1.5 rounded-full", ok ? "bg-positive" : "bg-caution")}
          />
        )}
        {label}
      </dt>
      <dd className="mt-1 text-[17px] font-semibold text-text tabular-nums">{value}</dd>
    </div>
  );
}

export function DataQuality({ quality }: { quality?: DatasetQuality }) {
  if (!quality) {
    return (
      <Card className="space-y-4 p-5 sm:p-6" aria-busy="true" aria-label="Loading data quality">
        <Skeleton className="h-5 w-56" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-40 w-full" />
      </Card>
    );
  }

  const { title, body } = verdict(quality);
  return (
    <Card className="overflow-hidden">
      <div className="flex items-start gap-3 p-5 sm:p-6">
        <StatusIcon status={quality.status} className="mt-0.5 size-5 shrink-0" />
        <div>
          <h3 className="text-[15px] font-semibold text-text">{title}</h3>
          <p className="mt-0.5 text-[13px] leading-5 text-text-secondary">{body}</p>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-px border-y border-separator bg-separator sm:grid-cols-4">
        <Measure
          label="Missing values"
          value={quality.missing_values.toLocaleString("en")}
          ok={quality.missing_values === 0}
        />
        <Measure
          label="Duplicate rows"
          value={quality.duplicate_rows.toLocaleString("en")}
          ok={quality.duplicate_rows === 0}
        />
        <Measure
          label="Invalid values"
          value={quality.invalid_values.toLocaleString("en")}
          ok={quality.invalid_values === 0}
        />
        <Measure
          label="Dimensions"
          value={`${quality.rows.toLocaleString("en")} × ${quality.columns}`}
        />
      </dl>

      <ul className="divide-y divide-separator" aria-label="Validation checks">
        {quality.checks.map((check) => (
          <li key={check.key} className="flex items-start gap-3 px-5 py-3 sm:px-6">
            <StatusIcon status={check.status} className="mt-px shrink-0" />
            <div className="min-w-0">
              <p className="text-[14px] font-medium text-text">{check.title}</p>
              <p className="mt-0.5 text-[13px] leading-[19px] text-text-secondary">
                {check.summary}
              </p>
            </div>
          </li>
        ))}
      </ul>

      {quality.column_issues.length > 0 && (
        <div className="border-t border-separator px-5 py-4 sm:px-6">
          <p className="text-[12px] font-medium text-text-secondary">Affected columns</p>
          <ul className="mt-2 space-y-1 text-[13px] text-text">
            {quality.column_issues.map((issue) => (
              <li key={issue.name}>
                <span className="font-mono text-[12px]">{issue.name}</span>
                <span className="text-text-secondary">
                  {issue.missing > 0 && ` · ${issue.missing} missing`}
                  {issue.invalid > 0 &&
                    ` · ${issue.invalid} invalid (e.g. ${issue.invalid_examples
                      .map((v) => `“${v}”`)
                      .join(", ")})`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {quality.observations.length > 0 && (
        <div className="border-t border-separator bg-surface-muted px-5 py-4 sm:px-6">
          <p className="text-[12px] font-medium text-text-secondary">Worth knowing</p>
          <ul className="mt-2 space-y-3">
            {quality.observations.map((note) => (
              <li key={note.key} className="flex items-start gap-3">
                <StatusIcon status="info" className="mt-px shrink-0" />
                <div>
                  <p className="text-[14px] font-medium text-text">{note.title}</p>
                  <p className="mt-0.5 text-[13px] leading-[19px] text-text-secondary">
                    {note.detail}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="border-t border-separator px-5 py-3 text-[12px] text-text-tertiary sm:px-6">
        Checks compare each value with the UCI documentation. They report problems but never delete
        or alter data.
      </p>
    </Card>
  );
}
