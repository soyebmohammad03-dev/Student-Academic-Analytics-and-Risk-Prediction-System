import type { Metadata } from "next";

import { PredictionView } from "@/components/prediction/PredictionView";
import { ClientView } from "@/components/layout/ClientView";

export const metadata: Metadata = { title: "Prediction" };

export default function PredictionPage() {
  return (
    <ClientView>
      <PredictionView />
    </ClientView>
  );
}
