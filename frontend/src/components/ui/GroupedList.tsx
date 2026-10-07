import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/cn";

/** Inset grouped list: a single rounded surface with hairline-separated rows. */
export function GroupedList({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <ul
      className={cn(
        "divide-y divide-separator overflow-hidden rounded-2xl bg-surface shadow-card",
        className,
      )}
    >
      {children}
    </ul>
  );
}

interface RowProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
  href?: string;
}

export function ListRow({ title, description, leading, trailing, href }: RowProps) {
  const content = (
    <>
      {leading && <div className="shrink-0">{leading}</div>}
      <div className="min-w-0 flex-1">
        <div className="text-[14px] leading-5 font-medium text-text">{title}</div>
        {description && (
          <div className="mt-0.5 text-[13px] leading-[18px] text-text-secondary">{description}</div>
        )}
      </div>
      {trailing && <div className="flex shrink-0 items-center gap-2">{trailing}</div>}
      {href && (
        <ChevronRight className="size-4 shrink-0 text-text-tertiary" strokeWidth={2} aria-hidden />
      )}
    </>
  );

  const rowClass = "flex items-center gap-3.5 px-4 py-3 sm:px-5";

  return (
    <li>
      {href ? (
        <Link
          href={href}
          className={cn(
            rowClass,
            "transition-colors duration-150 hover:bg-fill focus-visible:rounded-none",
          )}
        >
          {content}
        </Link>
      ) : (
        <div className={rowClass}>{content}</div>
      )}
    </li>
  );
}

/** Small rounded-square icon tile used as a row's leading element. */
export function IconTile({ children }: { children: React.ReactNode }) {
  return (
    <span className="flex size-8 items-center justify-center rounded-[9px] bg-fill text-text-secondary">
      {children}
    </span>
  );
}
