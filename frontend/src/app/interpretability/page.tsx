import type { Metadata } from "next";

import { InterpretabilityView } from "@/components/interpret/InterpretabilityView";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Interpretability" };

export default function InterpretabilityPage() {
  return (
    <ClientView>
      <InterpretabilityView />
    </ClientView>
  );
}
