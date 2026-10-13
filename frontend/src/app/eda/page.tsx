import type { Metadata } from "next";

import { EdaView } from "@/components/eda/EdaView";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Exploratory Analysis" };

export default function EdaPage() {
  return (
    <ClientView>
      <EdaView />
    </ClientView>
  );
}
