import { cn } from "@/lib/cn";

type Tone = "neutral" | "accent" | "positive" | "caution" | "critical";

const tones: Record<Tone, string> = {
  neutral: "bg-fill text-text-secondary",
  accent: "bg-accent-soft text-accent",
  positive: "bg-positive-soft text-positive",
  caution: "bg-caution-soft text-caution",
  critical: "bg-critical-soft text-critical",
};

export function StatusBadge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full px-2 text-[11px] font-medium tracking-[0.01em] whitespace-nowrap",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function PhaseBadge({ phase }: { phase: number }) {
  return <StatusBadge>Phase {phase}</StatusBadge>;
}
