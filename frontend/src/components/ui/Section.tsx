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
      <div className="flex items-end justify-between gap-4 px-1">
        <div>
          <h2 className="font-display text-[15px] font-semibold tracking-[-0.01em] text-text">
            {title}
          </h2>
          {description && (
            <p className="mt-0.5 text-[13px] leading-5 text-text-secondary">{description}</p>
          )}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
