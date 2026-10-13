import { CircleAlert, Info, ShieldCheck } from "lucide-react";

import { cn } from "@/lib/cn";

const tones = {
  info: { icon: Info, className: "bg-accent-soft text-accent" },
  caution: { icon: CircleAlert, className: "bg-caution-soft text-caution" },
  responsible: { icon: ShieldCheck, className: "bg-fill text-text-secondary" },
} as const;

/** A short, tinted note: limitations, disclaimers and reading guidance. */
export function Callout({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: keyof typeof tones;
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const { icon: Icon, className: toneClass } = tones[tone];
  return (
    <div className={cn("flex gap-3 rounded-2xl bg-surface p-4 shadow-card sm:p-5", className)}>
      <span
        className={cn("flex size-7 shrink-0 items-center justify-center rounded-[9px]", toneClass)}
      >
        <Icon className="size-4" strokeWidth={2} aria-hidden />
      </span>
      <div className="min-w-0 text-[13px] leading-5 text-text-secondary">
        {title && <p className="mb-0.5 font-semibold text-text">{title}</p>}
        {children}
      </div>
    </div>
  );
}

/** Distinguishes the kind of a result: what was observed versus what a model produced. */
export function KindBadge({
  kind,
}: {
  kind: "observed" | "model_evaluation" | "prediction" | "explanation" | "sensitivity";
}) {
  const config = {
    observed: ["Observed · historical data", "bg-positive-soft text-positive"],
    model_evaluation: ["Model evaluation", "bg-accent-soft text-accent"],
    prediction: ["Model prediction", "bg-caution-soft text-caution"],
    explanation: ["Model explanation", "bg-fill-strong text-text-secondary"],
    sensitivity: ["Model sensitivity experiment", "bg-fill-strong text-text-secondary"],
  } as const;
  const [label, className] = config[kind];
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full px-2 text-[11px] font-medium whitespace-nowrap",
        className,
      )}
    >
      {label}
    </span>
  );
}
