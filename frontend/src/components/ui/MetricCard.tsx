import { cn } from "@/lib/cn";

import { InfoTip } from "./InfoTip";

/** One headline number with its label, an optional explanation and context line. */
export function MetricCard({
  label,
  value,
  unit,
  hint,
  info,
  className,
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  hint?: React.ReactNode;
  info?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 bg-surface px-5 py-4", className)}>
      <dt className="flex items-center gap-1 text-[12px] font-medium text-text-secondary">
        {label}
        {info && <InfoTip label={`About ${label}`}>{info}</InfoTip>}
      </dt>
      <dd className="mt-1.5 font-display text-[26px] leading-none font-semibold tracking-[-0.02em] text-text tabular-nums">
        {value}
        {unit && (
          <span className="ml-1 text-[14px] font-medium tracking-normal text-text-tertiary">
            {unit}
          </span>
        )}
      </dd>
      {hint && (
        <dd className="mt-2 text-[11px] leading-4 text-text-tertiary tabular-nums">{hint}</dd>
      )}
    </div>
  );
}

/** Hairline grid of metric cards on one surface. */
export function MetricGrid({
  children,
  className,
  label,
}: {
  children: React.ReactNode;
  className?: string;
  label?: string;
}) {
  return (
    <dl
      aria-label={label}
      className={cn(
        "grid grid-cols-2 gap-px overflow-hidden rounded-2xl bg-separator shadow-card",
        className,
      )}
    >
      {children}
    </dl>
  );
}
