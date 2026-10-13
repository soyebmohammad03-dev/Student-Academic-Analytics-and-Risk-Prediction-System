import type { Metadata } from "next";

import { DataExplorer } from "@/components/data-explorer/DataExplorer";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Data Explorer" };

export default function DataExplorerPage() {
  return (
    <ClientView>
      <DataExplorer />
    </ClientView>
  );
}
