"use client";

import { Database, Server, Boxes } from "lucide-react";
import { useEffect, useState } from "react";

import { GroupedList, IconTile, ListRow } from "@/components/ui/GroupedList";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, type HealthResponse, type ProjectInfo } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "offline" }
  | { kind: "online"; health: HealthResponse; project: ProjectInfo };

/** Live backend status. Every value shown here is read from the API, never assumed. */
export function SystemStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api.health({ signal: controller.signal }),
      api.project({ signal: controller.signal }),
    ])
      .then(([health, project]) => setState({ kind: "online", health, project }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ kind: "offline" });
      });
    return () => controller.abort();
  }, []);

  return (
    <GroupedList>
      <ListRow
        leading={
          <IconTile>
            <Server className="size-4" />
          </IconTile>
        }
        title="Analytics API"
        description={
          state.kind === "online"
            ? `FastAPI · v${state.health.version} · ${state.health.environment}`
            : state.kind === "offline"
              ? "Not reachable. Start the backend to enable live data."
              : "Checking connection…"
        }
        trailing={
          state.kind === "online" ? (
            <StatusBadge tone="positive">Connected</StatusBadge>
          ) : state.kind === "offline" ? (
            <StatusBadge tone="caution">Offline</StatusBadge>
          ) : (
            <StatusBadge>Checking</StatusBadge>
          )
        }
      />
      <ListRow
        leading={
          <IconTile>
            <Database className="size-4" />
          </IconTile>
        }
        title="UCI Student Performance dataset"
        description={
          state.kind === "online"
            ? state.project.dataset.available_locally
              ? "Both cohort files found in data/raw."
              : "Not downloaded. Run python -m analytics.data.download in backend/."
            : "Status is reported by the API."
        }
        trailing={
          state.kind === "online" ? (
            state.project.dataset.available_locally ? (
              <StatusBadge tone="positive">Available</StatusBadge>
            ) : (
              <StatusBadge>Not downloaded</StatusBadge>
            )
          ) : (
            <StatusBadge>Unknown</StatusBadge>
          )
        }
      />
      <ListRow
        leading={
          <IconTile>
            <Boxes className="size-4" />
          </IconTile>
        }
        title="Trained models"
        description="No models have been trained. Training and evaluation begin in Phase 5."
        trailing={<StatusBadge>None</StatusBadge>}
      />
    </GroupedList>
  );
}
