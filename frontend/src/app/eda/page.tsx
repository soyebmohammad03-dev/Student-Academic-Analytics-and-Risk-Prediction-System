import type { Metadata } from "next";

import { ModulePlaceholder } from "@/components/ModulePlaceholder";
import { getModule } from "@/lib/modules";

const appModule = getModule("eda");

export const metadata: Metadata = { title: appModule.title };

export default function EdaPage() {
  return <ModulePlaceholder module={appModule} />;
}
