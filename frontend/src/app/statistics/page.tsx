import type { Metadata } from "next";

import { StatisticsView } from "@/components/statistics/StatisticsView";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Statistical Analysis" };

export default function StatisticsPage() {
  return (
    <ClientView>
      <StatisticsView />
    </ClientView>
  );
}
