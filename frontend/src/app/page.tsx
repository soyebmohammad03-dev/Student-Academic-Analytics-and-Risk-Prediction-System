import { DashboardView } from "@/components/dashboard/DashboardView";
import { ClientView } from "@/components/layout/ClientView";

export default function DashboardPage() {
  return (
    <ClientView>
      <DashboardView />
    </ClientView>
  );
}
