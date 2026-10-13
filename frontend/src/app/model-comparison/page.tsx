import type { Metadata } from "next";
import { Suspense } from "react";

import { ModelComparisonView } from "@/components/models/ModelComparisonView";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Model Comparison" };

export default function ModelComparisonPage() {
  return (
    // Reads ?cohort= and ?scenario= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <ModelComparisonView />
    </Suspense>
  );
}
