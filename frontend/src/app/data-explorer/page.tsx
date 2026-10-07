import type { Metadata } from "next";

import { ModulePlaceholder } from "@/components/ModulePlaceholder";
import { getModule } from "@/lib/modules";

const appModule = getModule("data");

export const metadata: Metadata = { title: appModule.title };

export default function DataExplorerPage() {
  return <ModulePlaceholder module={appModule} />;
}
