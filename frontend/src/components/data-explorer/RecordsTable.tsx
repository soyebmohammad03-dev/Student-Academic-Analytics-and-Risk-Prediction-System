"use client";

import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import type { ColumnInfo, DatasetRecords } from "@/lib/api";
import { cn } from "@/lib/cn";

export function RecordsTable({
  records,
  columns,
  loading,
  searchInput,
  onSearchInput,
  onPage,
}: {
  records?: DatasetRecords;
  columns?: ColumnInfo[];
  loading: boolean;
  searchInput: string;
  onSearchInput: (value: string) => void;
  onPage: (page: number) => void;
}) {
  const info = new Map(columns?.map((c) => [c.name, c]));
  const first = records && records.total ? (records.page - 1) * records.page_size + 1 : 0;
  const last = records ? first + records.items.length - (records.items.length ? 1 : 0) : 0;

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-separator p-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
        <label className="relative flex-1 sm:max-w-xs">
          <span className="sr-only">Search records</span>
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-text-tertiary"
          />
          <input
            type="search"
            value={searchInput}
            onChange={(e) => onSearchInput(e.target.value)}
            placeholder="Search any value, e.g. teacher"
            maxLength={100}
            className="h-8 w-full rounded-lg bg-fill pr-8 pl-8 text-[13px] text-text placeholder:text-text-tertiary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent [&::-webkit-search-cancel-button]:hidden"
          />
          {searchInput && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => onSearchInput("")}
              className="absolute top-1/2 right-2 -translate-y-1/2 rounded-full p-0.5 text-text-tertiary hover:text-text"
            >
              <X className="size-3.5" />
            </button>
          )}
        </label>
        <p className="text-[12px] text-text-secondary tabular-nums" aria-live="polite">
          {records
            ? records.search
              ? `${records.total.toLocaleString("en")} matching ${records.total === 1 ? "student" : "students"}`
              : `${records.total.toLocaleString("en")} students`
            : "Loading…"}
        </p>
      </div>

      {!records ? (
        <div className="space-y-2 p-4" aria-busy="true" aria-label="Loading records">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
      ) : records.items.length === 0 ? (
        <div className="px-6 py-16 text-center">
          <p className="text-[14px] font-medium text-text">
            {records.search ? `No students match “${records.search}”` : "No rows on this page"}
          </p>
          <p className="mt-1 text-[13px] text-text-secondary">
            {records.search
              ? "Search looks for the text inside any value, such as a job, school code or grade."
              : "Go back to the first page to see the records."}
          </p>
        </div>
      ) : (
        <div
          // Scrollable in both directions, so keyboard users must be able to focus it.
          tabIndex={0}
          role="region"
          aria-label="Student records (scrollable)"
          className={cn(
            "max-h-[560px] overflow-auto transition-opacity duration-200",
            loading && "opacity-60",
          )}
        >
          <table className="w-full border-separate border-spacing-0 text-left text-[13px]">
            <caption className="sr-only">
              Student records, rows {first} to {last}
            </caption>
            <thead>
              <tr>
                <th
                  scope="col"
                  className="sticky top-0 left-0 z-20 border-b border-separator bg-surface-muted px-3 py-2 text-[11px] font-medium text-text-tertiary"
                >
                  Row
                </th>
                {records.columns.map((name) => {
                  const column = info.get(name);
                  return (
                    <th
                      key={name}
                      scope="col"
                      title={column ? `${column.label}: ${column.description}` : undefined}
                      className={cn(
                        "sticky top-0 z-10 border-b border-separator bg-surface-muted px-3 py-2 font-mono text-[11px] font-medium whitespace-nowrap",
                        column?.role === "target" ? "text-accent" : "text-text-secondary",
                        column?.measure === "numerical" && "text-right",
                      )}
                    >
                      {name}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {records.items.map((item) => (
                <tr key={item.row} className="group">
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border-b border-separator bg-surface px-3 py-2 text-[12px] font-normal text-text-tertiary tabular-nums group-hover:bg-surface-muted"
                  >
                    {item.row}
                  </th>
                  {records.columns.map((name) => {
                    const value = item.values[name];
                    const column = info.get(name);
                    return (
                      <td
                        key={name}
                        className={cn(
                          "border-b border-separator px-3 py-2 whitespace-nowrap text-text group-hover:bg-surface-muted",
                          typeof value === "number" && "text-right tabular-nums",
                          column?.role === "target" && "font-semibold",
                        )}
                      >
                        {value ?? <span className="text-text-tertiary">—</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {records && records.total > 0 && (
        <nav
          aria-label="Pagination"
          className="flex items-center justify-between gap-3 border-t border-separator px-3 py-2.5 sm:px-4"
        >
          <p className="text-[12px] text-text-secondary tabular-nums">
            Rows {first}–{last} of {records.total.toLocaleString("en")}
          </p>
          <div className="flex items-center gap-1">
            <span className="mr-2 text-[12px] text-text-tertiary tabular-nums">
              Page {records.page} of {records.total_pages}
            </span>
            <PageButton
              label="Previous page"
              disabled={records.page <= 1}
              onClick={() => onPage(records.page - 1)}
            >
              <ChevronLeft className="size-4" />
            </PageButton>
            <PageButton
              label="Next page"
              disabled={records.page >= records.total_pages}
              onClick={() => onPage(records.page + 1)}
            >
              <ChevronRight className="size-4" />
            </PageButton>
          </div>
        </nav>
      )}
    </Card>
  );
}

function PageButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="flex size-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-fill hover:text-text disabled:pointer-events-none disabled:opacity-30"
    >
      {children}
    </button>
  );
}
