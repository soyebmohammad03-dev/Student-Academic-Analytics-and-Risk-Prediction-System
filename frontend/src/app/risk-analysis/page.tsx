import type { Metadata } from "next";

import { RiskAnalysisView } from "@/components/risk/RiskAnalysisView";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Risk Analysis" };

export default function RiskAnalysisPage() {
  return (
    <ClientView>
      <RiskAnalysisView />
    </ClientView>
  );
}
