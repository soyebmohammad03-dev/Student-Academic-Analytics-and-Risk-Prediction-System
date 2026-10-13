import type { Metadata } from "next";
import { Suspense } from "react";

import { RiskAnalysisView } from "@/components/risk/RiskAnalysisView";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Risk Analysis" };

export default function RiskAnalysisPage() {
  return (
    // Reads ?cohort= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <RiskAnalysisView />
    </Suspense>
  );
}
