import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/cn";

const control =
  "h-9 w-full rounded-[10px] border bg-surface px-3 text-[14px] text-text transition-colors outline-none focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-accent";

/** Labelled form control with an optional hint and validation message. */
export function Field({
  id,
  label,
  hint,
  error,
  children,
  className,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <label htmlFor={id} className="mb-1 block text-[12px] font-medium text-text-secondary">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-[12px] leading-4 text-critical">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-1 text-[11px] leading-4 text-text-tertiary">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

export function controlClass(invalid?: boolean) {
  return cn(control, invalid ? "border-critical" : "border-separator hover:border-fill-strong");
}

export function SelectControl({
  invalid,
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }) {
  return (
    <span className="relative block">
      <select
        {...props}
        aria-invalid={invalid || undefined}
        className={cn(controlClass(invalid), "appearance-none pr-8", className)}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-text-tertiary"
        aria-hidden
      />
    </span>
  );
}
