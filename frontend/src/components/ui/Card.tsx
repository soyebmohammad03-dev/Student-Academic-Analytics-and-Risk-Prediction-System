import { cn } from "@/lib/cn";

export function Card({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-2xl bg-surface shadow-card", className)} {...props}>
      {children}
    </div>
  );
}
