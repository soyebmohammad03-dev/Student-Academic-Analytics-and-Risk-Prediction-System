import { CloudOff, DatabaseZap, RotateCw } from "lucide-react";

import { Card } from "@/components/ui/Card";
import type { ApiError } from "@/lib/api";

/** Full-width explanation for why data could not be shown, with the fix. */
export function DataUnavailable({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  const missingDataset = error.code === "dataset_unavailable";
  const offline = error.status === undefined;
  const Icon = missingDataset ? DatabaseZap : CloudOff;

  return (
    <Card className="flex flex-col items-center px-6 py-14 text-center" role="alert">
      <span className="flex size-12 items-center justify-center rounded-[14px] bg-fill text-text-secondary">
        <Icon className="size-6" strokeWidth={1.75} />
      </span>
      <h2 className="mt-5 font-display text-[17px] font-semibold tracking-[-0.01em] text-text">
        {missingDataset
          ? "The dataset has not been downloaded"
          : offline
            ? "The analytics API is not reachable"
            : "The data could not be loaded"}
      </h2>
      <p className="mt-1.5 max-w-md text-[14px] leading-[21px] text-text-secondary">
        {missingDataset
          ? "Download and verify the official UCI files, then try again:"
          : offline
            ? "Start the backend, then try again:"
            : error.message}
      </p>
      {(missingDataset || offline) && (
        <code className="mt-4 rounded-lg bg-fill px-3 py-2 font-mono text-[12px] text-text">
          {missingDataset
            ? "cd backend && python -m analytics.data.download"
            : "cd backend && uvicorn app.main:app --port 8000"}
        </code>
      )}
      <button
        type="button"
        onClick={onRetry}
        className="mt-6 inline-flex h-8 items-center gap-1.5 rounded-full bg-fill px-4 text-[13px] font-medium text-text transition-colors hover:bg-fill-strong"
      >
        <RotateCw className="size-3.5" />
        Try again
      </button>
    </Card>
  );
}
