import { cn } from "@/lib/cn";

export function Section({
  title,
  description,
  action,
  children,
  className,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("space-y-3", className)}>
      <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
        <div>
          <h2 className="font-display text-[15px] font-semibold tracking-[-0.01em] text-text">
            {title}
          </h2>
          {description && (
            <p className="mt-0.5 text-[13px] leading-5 text-text-secondary">{description}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </section>
  );
}
