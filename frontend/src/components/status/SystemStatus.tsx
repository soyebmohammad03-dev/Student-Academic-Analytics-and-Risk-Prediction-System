import { Boxes, ChartScatter, Database, ScanSearch, Server } from "lucide-react";

import { GroupedList, IconTile, ListRow } from "@/components/ui/GroupedList";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ComponentStatus } from "@/lib/api";

const icons = {
  api: Server,
  dataset: Database,
  statistics: ChartScatter,
  models: Boxes,
  interpretability: ScanSearch,
} as const;

const badge = {
  available: ["positive", "Available"],
  degraded: ["caution", "Degraded"],
  unavailable: ["neutral", "Unavailable"],
} as const;

/** Readiness of each backend component, exactly as reported by GET /ready. */
export function SystemStatus({ components }: { components: ComponentStatus[] }) {
  return (
    <GroupedList>
      {components.map((c) => {
        const Icon = icons[c.key] ?? Server;
        const [tone, label] = badge[c.status];
        return (
          <ListRow
            key={c.key}
            leading={
              <IconTile>
                <Icon className="size-4" />
              </IconTile>
            }
            title={c.label}
            description={
              <>
                {c.detail}
                {c.action && (
                  <code className="mt-1.5 block w-fit max-w-full overflow-x-auto rounded-md bg-fill px-2 py-1 font-mono text-[11px] whitespace-nowrap text-text">
                    {c.action}
                  </code>
                )}
              </>
            }
            trailing={<StatusBadge tone={tone}>{label}</StatusBadge>}
          />
        );
      })}
    </GroupedList>
  );
}
