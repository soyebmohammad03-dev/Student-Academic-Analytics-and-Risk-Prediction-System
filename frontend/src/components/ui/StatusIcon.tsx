import { CircleAlert, CircleCheck, CircleX, Info } from "lucide-react";

import { cn } from "@/lib/cn";

export type StatusTone = "pass" | "warning" | "fail" | "info";

const config = {
  pass: { icon: CircleCheck, className: "text-positive", label: "Passed" },
  warning: { icon: CircleAlert, className: "text-caution", label: "Warning" },
  fail: { icon: CircleX, className: "text-critical", label: "Failed" },
  info: { icon: Info, className: "text-accent", label: "Note" },
} as const;

export function StatusIcon({ status, className }: { status: StatusTone; className?: string }) {
  const { icon: Icon, className: tone, label } = config[status];
  return <Icon role="img" aria-label={label} className={cn("size-[18px]", tone, className)} />;
}
