import type { Metadata } from "next";

import { ModulePlaceholder } from "@/components/ModulePlaceholder";
import { getModule } from "@/lib/modules";

const appModule = getModule("statistics");

export const metadata: Metadata = { title: appModule.title };

export default function StatisticsPage() {
  return <ModulePlaceholder module={appModule} />;
}
