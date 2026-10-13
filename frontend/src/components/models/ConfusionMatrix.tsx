import type { Confusion } from "@/lib/models";

/**
 * 2 × 2 confusion matrix (rows: actual, columns: predicted; positive = at risk).
 * Shading encodes the share of each actual class, so the reading does not depend on
 * class sizes; counts and row shares are printed in every cell.
 */
export function ConfusionMatrix({ confusion, caption }: { confusion: Confusion; caption: string }) {
  const { tn, fp, fn, tp } = confusion;
  const rows = [
    {
      label: "At risk",
      cells: [
        { v: tp, correct: true, name: "Flagged (true positive)" },
        { v: fn, correct: false, name: "Missed (false negative)" },
      ],
    },
    {
      label: "Not at risk",
      cells: [
        { v: fp, correct: false, name: "Flagged (false positive)" },
        { v: tn, correct: true, name: "Not flagged (true negative)" },
      ],
    },
  ];
  return (
    <table className="w-full table-fixed border-separate border-spacing-1 text-[13px]">
      <caption className="mb-2 text-left text-[12px] text-text-secondary">{caption}</caption>
      <thead>
        <tr className="text-[11px] text-text-tertiary">
          <th scope="col" className="w-[30%] text-left font-medium">
            Actual ↓ · Predicted →
          </th>
          <th scope="col" className="font-medium">
            At risk
          </th>
          <th scope="col" className="font-medium">
            Not at risk
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const total = row.cells[0].v + row.cells[1].v;
          return (
            <tr key={row.label}>
              <th
                scope="row"
                className="pr-2 text-left text-[12px] font-medium text-text-secondary"
              >
                {row.label}
                <span className="block text-[11px] font-normal text-text-tertiary tabular-nums">
                  n = {total}
                </span>
              </th>
              {row.cells.map((cell) => {
                const share = total ? cell.v / total : 0;
                return (
                  <td
                    key={cell.name}
                    title={cell.name}
                    className="rounded-xl px-2 py-3 text-center tabular-nums"
                    style={{
                      background: `color-mix(in srgb, ${cell.correct ? "var(--chart-1)" : "var(--chart-2)"} ${Math.round(8 + 40 * share)}%, transparent)`,
                    }}
                  >
                    <span className="block font-display text-[20px] leading-none font-semibold text-text">
                      {cell.v}
                    </span>
                    <span className="mt-1 block text-[11px] text-text-secondary">
                      {(100 * share).toFixed(0)}% · {cell.name.split(" (")[0]}
                    </span>
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
