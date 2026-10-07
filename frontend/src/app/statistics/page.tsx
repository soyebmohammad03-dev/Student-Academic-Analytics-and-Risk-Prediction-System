import type { Metadata } from "next";
import { Suspense } from "react";

import { StatisticsView } from "@/components/statistics/StatisticsView";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Statistical Analysis" };

export default function StatisticsPage() {
  return (
    // Reads ?cohort= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <StatisticsView />
    </Suspense>
  );
}
