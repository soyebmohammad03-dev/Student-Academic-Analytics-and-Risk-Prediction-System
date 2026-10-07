import type { Metadata } from "next";
import { Suspense } from "react";

import { DataExplorer } from "@/components/data-explorer/DataExplorer";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Data Explorer" };

export default function DataExplorerPage() {
  return (
    // The explorer reads ?cohort= from the URL, so it renders on the client.
    <Suspense
      fallback={
        <div className="space-y-6" aria-busy="true">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-48 w-full rounded-2xl" />
        </div>
      }
    >
      <DataExplorer />
    </Suspense>
  );
}
