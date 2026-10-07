import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fmt, fmtP } from "@/lib/format";
import type { ResearchQuestions as Data } from "@/lib/statistics";

export function ResearchQuestions({ data }: { data: Data }) {
  return (
    <div className="space-y-3">
      <ul className="divide-y divide-separator overflow-hidden rounded-2xl bg-surface shadow-card">
        {data.items.map((q) => (
          <li key={q.key} className="space-y-2 px-5 py-4 sm:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[12px] font-semibold text-text-secondary">
                {q.key}
              </span>
              <StatusBadge>{q.evidence}</StatusBadge>
              {q.significant ? (
                <StatusBadge tone="accent">Significant after correction</StatusBadge>
              ) : (
                <StatusBadge>Not significant</StatusBadge>
              )}
            </div>
            <p className="text-[15px] font-medium text-text">{q.question}</p>
            <dl className="grid gap-x-6 gap-y-1 text-[12px] sm:grid-cols-4">
              <div>
                <dt className="text-text-tertiary">Test</dt>
                <dd className="text-text">{q.test}</dd>
              </div>
              <div>
                <dt className="text-text-tertiary">Adjusted p</dt>
                <dd className="text-text tabular-nums">{fmtP(q.p_adjusted)}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-text-tertiary">Effect size</dt>
                <dd className="text-text tabular-nums">
                  {q.effect ? (
                    <>
                      {q.effect.name} = {fmt(q.effect.value)}
                      {q.effect.ci && q.effect.ci.low !== null && (
                        <span className="text-text-secondary">
                          {" "}
                          [{fmt(q.effect.ci.low)}, {fmt(q.effect.ci.high)}]
                        </span>
                      )}{" "}
                      <span className="text-text-secondary">· {q.effect.magnitude}</span>
                    </>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
            </dl>
            <p className="text-[13px] leading-[20px] text-text-secondary">{q.finding}</p>
            {q.sensitivity && (
              <p className="text-[12px] leading-[18px] text-text-tertiary">{q.sensitivity}</p>
            )}
          </li>
        ))}
      </ul>
      <Card className="px-5 py-3 text-[12px] leading-[18px] text-text-secondary sm:px-6">
        α = {data.alpha}. {data.correction} Confidence intervals are 95% and unadjusted. Statistical
        significance indicates an association in these data, not a cause.
      </Card>
    </div>
  );
}
