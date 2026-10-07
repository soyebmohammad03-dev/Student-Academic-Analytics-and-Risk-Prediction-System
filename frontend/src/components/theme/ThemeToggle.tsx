"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import { cn } from "@/lib/cn";

import {
  applyThemePreference,
  readThemePreference,
  subscribeToTheme,
  type ThemePreference,
} from "./theme";

const options: Array<{ value: ThemePreference; label: string; icon: typeof Sun }> = [
  { value: "system", label: "System", icon: Monitor },
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
];

export function ThemeToggle({ className }: { className?: string }) {
  const preference = useSyncExternalStore(
    subscribeToTheme,
    readThemePreference,
    () => "system" as const,
  );

  return (
    <div
      role="radiogroup"
      aria-label="Appearance"
      className={cn("grid grid-cols-3 gap-0.5 rounded-[9px] bg-fill p-0.5", className)}
    >
      {options.map(({ value, label, icon: Icon }) => {
        const selected = preference === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={label}
            title={label}
            onClick={() => applyThemePreference(value)}
            className={cn(
              "flex h-7 items-center justify-center rounded-[7px] transition-all duration-200",
              selected
                ? "bg-surface text-text shadow-card"
                : "text-text-tertiary hover:text-text-secondary",
            )}
          >
            <Icon className="size-3.5" strokeWidth={2} aria-hidden />
          </button>
        );
      })}
    </div>
  );
}
