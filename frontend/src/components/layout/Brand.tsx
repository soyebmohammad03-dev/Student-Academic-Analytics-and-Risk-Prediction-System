import Link from "next/link";

/** Abstract mark: three ascending bars inside a rounded square. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="8" className="fill-text" />
      <rect x="8" y="17" width="4" height="7" rx="1.5" className="fill-bg" opacity="0.55" />
      <rect x="14" y="12" width="4" height="12" rx="1.5" className="fill-bg" opacity="0.8" />
      <rect x="20" y="8" width="4" height="16" rx="1.5" className="fill-bg" />
    </svg>
  );
}

export function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 rounded-lg">
      <BrandMark className="size-7 shrink-0" />
      <span className="flex flex-col leading-tight">
        <span className="text-[13px] font-semibold tracking-[-0.01em] text-text">
          Student Academic Analytics
        </span>
        <span className="text-[11px] text-text-tertiary">and Risk Prediction System</span>
      </span>
    </Link>
  );
}
