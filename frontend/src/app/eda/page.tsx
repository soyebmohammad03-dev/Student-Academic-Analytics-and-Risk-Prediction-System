import type { Metadata } from "next";
import { Suspense } from "react";

import { EdaView } from "@/components/eda/EdaView";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = { title: "Exploratory Analysis" };

export default function EdaPage() {
  return (
    // Reads ?cohort= from the URL, so it renders on the client.
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-2xl" />}>
      <EdaView />
    </Suspense>
  );
}
