import type { Metadata } from "next";
import { Suspense } from "react";

import { PredictionView } from "@/components/prediction/PredictionView";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Prediction" };

export default function PredictionPage() {
  return (
    // Reads ?cohort= and ?scenario= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <PredictionView />
    </Suspense>
  );
}
