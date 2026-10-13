import type { Metadata } from "next";

import { ModelComparisonView } from "@/components/models/ModelComparisonView";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Model Comparison" };

export default function ModelComparisonPage() {
  return (
    <ClientView>
      <ModelComparisonView />
    </ClientView>
  );
}
