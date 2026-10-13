import type { ValueCount } from "@/lib/statistics";

/**
 * Compact column chart of a 0–20 grade distribution. Grades below the pass mark use
 * the second series colour. Each column carries a native tooltip; the figure is
 * described for screen readers by its aria-label.
 */
export function GradeStrip({
  counts,
  passMark,
  label,
  max = 20,
}: {
  counts: ValueCount[];
  passMark: number;
  label: string;
  max?: number;
}) {
  const byGrade = new Map(counts.map((c) => [c.value, c.count]));
  const grades = Array.from({ length: max + 1 }, (_, g) => ({
    grade: g,
    count: byGrade.get(g) ?? 0,
  }));
  const top = Math.max(...grades.map((g) => g.count), 1);
  const total = grades.reduce((sum, g) => sum + g.count, 0);

  return (
    <figure className="min-w-0">
      <div className="flex h-16 items-end gap-[2px]" role="img" aria-label={label}>
        {grades.map((g) => (
          <span
            key={g.grade}
            title={`Grade ${g.grade}: ${g.count} students (${total ? ((100 * g.count) / total).toFixed(1) : 0}%)`}
            className="flex-1 rounded-t-[2px]"
            style={{
              height: `${Math.max((100 * g.count) / top, g.count ? 4 : 1)}%`,
              background: g.count
                ? g.grade < passMark
                  ? "var(--chart-2)"
                  : "var(--chart-1)"
                : "var(--fill-strong)",
            }}
          />
        ))}
      </div>
      <div
        className="mt-1 flex justify-between text-[10px] text-text-tertiary tabular-nums"
        aria-hidden
      >
        <span>0</span>
        <span>{passMark}</span>
        <span>{max}</span>
      </div>
    </figure>
  );
}
