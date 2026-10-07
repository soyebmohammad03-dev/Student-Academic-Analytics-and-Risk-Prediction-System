import type { Metadata } from "next";

import { ModulePlaceholder } from "@/components/ModulePlaceholder";
import { getModule } from "@/lib/modules";

const appModule = getModule("risk");

export const metadata: Metadata = { title: appModule.title };

export default function RiskAnalysisPage() {
  return <ModulePlaceholder module={appModule} />;
}
