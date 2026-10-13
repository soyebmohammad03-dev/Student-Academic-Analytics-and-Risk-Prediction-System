"use client";

import { Info } from "lucide-react";
import { useId, useRef, useState } from "react";

import { cn } from "@/lib/cn";

const WIDTH = 256;

/**
 * Small "i" button that explains a term. It opens on hover and on keyboard focus,
 * closes with Escape, and is positioned against the viewport so scrolling tables
 * never clip it. The text is always in the DOM for screen readers (aria-describedby).
 */
export function InfoTip({
  label,
  children,
  className,
}: {
  /** Accessible name of the button, e.g. "What is recall?". */
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);

  function show() {
    const rect = button.current?.getBoundingClientRect();
    if (!rect) return;
    const left = Math.min(
      Math.max(8, rect.left + rect.width / 2 - WIDTH / 2),
      window.innerWidth - WIDTH - 8,
    );
    setPosition({ left, top: rect.bottom + 6 });
  }
  const hide = () => setPosition(null);

  return (
    // relative: keeps the visually hidden text inside any scrolling table, so it
    // cannot widen the page.
    <span className={cn("relative inline-flex align-middle", className)}>
      <button
        ref={button}
        type="button"
        aria-label={label}
        aria-describedby={id}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        onClick={() => (position ? hide() : show())}
        onKeyDown={(event) => event.key === "Escape" && hide()}
        className="inline-flex size-4 items-center justify-center rounded-full text-text-tertiary transition-colors hover:text-text-secondary"
      >
        <Info className="size-3.5" strokeWidth={2} aria-hidden />
      </button>
      <span
        id={id}
        role="tooltip"
        style={position ? { left: position.left, top: position.top, width: WIDTH } : undefined}
        className={cn(
          "pointer-events-none z-50 rounded-xl bg-surface px-3 py-2 text-left text-[12px] leading-[17px] font-normal tracking-normal whitespace-normal text-text-secondary normal-case shadow-raised",
          position ? "fixed" : "sr-only",
        )}
      >
        {children}
      </span>
    </span>
  );
}
