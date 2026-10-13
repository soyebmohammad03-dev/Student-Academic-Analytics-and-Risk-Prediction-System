import { Inbox } from "lucide-react";

import { cn } from "@/lib/cn";

import { Card } from "./Card";
import { Skeleton } from "./Skeleton";

/** Placeholder blocks while data loads; announced once to assistive technology. */
export function LoadingBlock({
  label,
  count = 1,
  height = "h-48",
  className,
}: {
  label: string;
  count?: number;
  height?: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label={label}
      className={cn("grid gap-3", count > 1 && "md:grid-cols-2", className)}
    >
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className={cn(height, "w-full rounded-2xl")} />
      ))}
    </div>
  );
}

/** Nothing to show yet, with what to do next. */
export function EmptyState({
  title,
  children,
  icon: Icon = Inbox,
}: {
  title: string;
  children?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}) {
  return (
    <Card className="flex flex-col items-center px-6 py-12 text-center">
      <span className="flex size-11 items-center justify-center rounded-[13px] bg-fill text-text-tertiary">
        <Icon className="size-5" strokeWidth={1.75} />
      </span>
      <p className="mt-4 text-[15px] font-semibold text-text">{title}</p>
      {children && (
        <div className="mt-1 max-w-md text-[13px] leading-5 text-text-secondary">{children}</div>
      )}
    </Card>
  );
}
