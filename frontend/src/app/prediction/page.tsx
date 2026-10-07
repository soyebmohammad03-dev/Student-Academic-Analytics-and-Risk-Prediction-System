import type { Metadata } from "next";

import { ModulePlaceholder } from "@/components/ModulePlaceholder";
import { getModule } from "@/lib/modules";

const appModule = getModule("prediction");

export const metadata: Metadata = { title: appModule.title };

export default function PredictionPage() {
  return <ModulePlaceholder module={appModule} />;
}
