import type { Metadata } from "next";
import { Suspense } from "react";

import { InterpretabilityView } from "@/components/interpret/InterpretabilityView";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Interpretability" };

export default function InterpretabilityPage() {
  return (
    // Reads ?cohort= and ?scenario= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <InterpretabilityView />
    </Suspense>
  );
}
