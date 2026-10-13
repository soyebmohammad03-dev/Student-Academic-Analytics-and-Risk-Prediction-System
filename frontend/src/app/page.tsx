import { Suspense } from "react";

import { DashboardView } from "@/components/dashboard/DashboardView";
import { Skeleton } from "@/components/ui/Skeleton";

export default function DashboardPage() {
  return (
    // Reads ?cohort= and ?scenario= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <DashboardView />
    </Suspense>
  );
}
