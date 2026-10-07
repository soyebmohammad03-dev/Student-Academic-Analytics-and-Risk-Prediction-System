import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import type { CohortOverlap as Overlap } from "@/lib/api";

function Row({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <li className="flex items-baseline justify-between gap-6 px-5 py-3 sm:px-6">
      <div>
        <p className="text-[14px] text-text">{label}</p>
        <p className="mt-0.5 text-[12px] text-text-tertiary">{hint}</p>
      </div>
      <span className="text-[15px] font-semibold text-text tabular-nums">{value}</span>
    </li>
  );
}

export function CohortOverlap({ overlap }: { overlap?: Overlap }) {
  if (!overlap) {
    return (
      <Card className="space-y-3 p-5" aria-busy="true" aria-label="Loading cohort overlap">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </Card>
    );
  }

  return (
    <Card>
      <ul className="divide-y divide-separator">
        <Row
          label="Likely the same student in both files"
          value={overlap.unambiguous_matches}
          hint="Profile is unique in both cohorts"
        />
        <Row
          label="Mathematics students with any match"
          value={overlap.math_rows_matched}
          hint={`of ${overlap.math_rows} in the Mathematics file`}
        />
        <Row
          label="Portuguese students with any match"
          value={overlap.portuguese_rows_matched}
          hint={`of ${overlap.portuguese_rows} in the Portuguese file`}
        />
        <Row
          label="Pairs from a plain join (UCI method)"
          value={overlap.join_pairs}
          hint={`${overlap.ambiguous_profiles} shared profiles match more than one student`}
        />
      </ul>
      <div className="space-y-2 border-t border-separator bg-surface-muted px-5 py-4 text-[12px] leading-[18px] text-text-secondary sm:px-6">
        <p>{overlap.method}</p>
        <p className="font-mono text-[11px] text-text-tertiary">
          {overlap.match_attributes.join(" · ")}
        </p>
        <p>{overlap.caveat}</p>
      </div>
    </Card>
  );
}
