import { cn } from "@/lib/cn";

export interface Column<T> {
  header: string;
  cell: (row: T) => React.ReactNode;
  align?: "left" | "right";
  className?: string;
}

/** Compact, scrollable table on a card surface. Numbers align right with tabular figures. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  caption?: string;
}) {
  return (
    <div
      tabIndex={0}
      role="region"
      aria-label={caption ? `${caption} (scrollable)` : "Table (scrollable)"}
      className="overflow-x-auto rounded-2xl bg-surface shadow-card"
    >
      <table className="w-full text-left text-[13px]">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-separator bg-surface-muted">
            {columns.map((c) => (
              <th
                key={c.header}
                scope="col"
                className={cn(
                  "px-4 py-2.5 text-[11px] font-medium whitespace-nowrap text-text-tertiary",
                  c.align === "right" && "text-right",
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-separator">
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td
                  key={c.header}
                  className={cn(
                    "px-4 py-2.5 text-text",
                    c.align === "right" && "text-right whitespace-nowrap tabular-nums",
                    c.className,
                  )}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
