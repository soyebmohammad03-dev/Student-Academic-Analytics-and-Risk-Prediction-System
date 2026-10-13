"use client";

import { Shuffle } from "lucide-react";
import { useId, useRef, useState } from "react";

import { controlClass } from "@/components/ui/Field";
import { type Cohort, type DatasetRecords, datasetPath, request } from "@/lib/api";

/**
 * Loads one row of the cohort file (by position, not identity) to fill a form. The
 * record is only held in memory for the form; nothing is stored in the browser.
 */
export function RecordPicker({
  cohort,
  total,
  onLoad,
}: {
  cohort: Cohort;
  total: number | undefined;
  onLoad: (row: number, values: DatasetRecords["items"][number]["values"]) => void;
}) {
  const id = useId();
  const [row, setRow] = useState("1");
  const [status, setStatus] = useState<{ loading: boolean; error?: string }>({ loading: false });
  const controller = useRef<AbortController | null>(null);

  async function load(target: number) {
    if (!Number.isInteger(target) || target < 1 || (total && target > total)) {
      setStatus({
        loading: false,
        error: `Enter a row from 1 to ${total ?? "the number of rows"}.`,
      });
      return;
    }
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setStatus({ loading: true });
    try {
      const page = await request<DatasetRecords>(
        datasetPath("records", cohort, { page: target, pageSize: 1 }),
        { signal: current.signal },
      );
      const item = page.items[0];
      if (!item) throw new Error("No record at that row.");
      onLoad(item.row, item.values);
      setStatus({ loading: false });
    } catch (error) {
      if (current.signal.aborted) return;
      setStatus({
        loading: false,
        error: error instanceof Error ? error.message : "Could not load the record.",
      });
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div>
        <label htmlFor={id} className="mb-1 block text-[12px] font-medium text-text-secondary">
          Start from row
        </label>
        <input
          id={id}
          type="number"
          min={1}
          max={total}
          value={row}
          onChange={(event) => setRow(event.target.value)}
          className={`${controlClass(Boolean(status.error))} w-24`}
        />
      </div>
      <button
        type="button"
        onClick={() => load(Number(row))}
        disabled={status.loading}
        className="h-9 rounded-full bg-fill px-4 text-[13px] font-medium text-text transition-colors hover:bg-fill-strong disabled:opacity-60"
      >
        {status.loading ? "Loading…" : "Load record"}
      </button>
      {total ? (
        <button
          type="button"
          onClick={() => {
            const random = 1 + Math.floor(Math.random() * total);
            setRow(String(random));
            void load(random);
          }}
          disabled={status.loading}
          className="inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium text-accent transition-colors hover:bg-accent-soft disabled:opacity-60"
        >
          <Shuffle className="size-3.5" aria-hidden />
          Random row
        </button>
      ) : null}
      {status.error && (
        <p role="alert" className="w-full text-[12px] text-critical">
          {status.error}
        </p>
      )}
    </div>
  );
}
