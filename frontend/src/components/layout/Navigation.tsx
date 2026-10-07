"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { cn } from "@/lib/cn";
import { aboutItem, analysisModules, dashboardItem, modellingModules } from "@/lib/modules";

import { Brand } from "./Brand";

type NavItem = { title: string; href: string; icon: React.ComponentType<{ className?: string }> };

const groups: Array<{ label?: string; items: NavItem[] }> = [
  { items: [dashboardItem] },
  { label: "Analysis", items: analysisModules },
  { label: "Modelling", items: modellingModules },
  { label: "Project", items: [aboutItem] },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Main" className="space-y-5">
      {groups.map((group, index) => (
        <div key={group.label ?? index}>
          {group.label && (
            <p className="mb-1 px-2.5 text-[11px] font-semibold tracking-[0.06em] text-text-tertiary uppercase">
              {group.label}
            </p>
          )}
          <ul className="space-y-px">
            {group.items.map(({ title, href, icon: Icon }) => {
              const active = isActive(pathname, href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-8 items-center gap-2.5 rounded-lg px-2.5 text-[13px] transition-colors duration-150",
                      active
                        ? "bg-fill-strong font-medium text-text"
                        : "text-text-secondary hover:bg-fill hover:text-text",
                    )}
                  >
                    <Icon
                      className={cn(
                        "size-4 shrink-0",
                        active ? "text-accent" : "text-text-tertiary",
                      )}
                    />
                    {title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function SidebarFooter() {
  return (
    <div className="space-y-2 border-t border-separator pt-4">
      <p className="px-0.5 text-[11px] font-medium text-text-tertiary">Appearance</p>
      <ThemeToggle />
    </div>
  );
}

/** Persistent sidebar on large screens. */
export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-separator bg-surface-translucent backdrop-blur-xl backdrop-saturate-150 lg:flex">
      <div className="px-5 pt-5 pb-6">
        <Brand />
      </div>
      <div className="flex-1 overflow-y-auto px-3">
        <NavLinks />
      </div>
      <div className="p-4">
        <SidebarFooter />
      </div>
    </aside>
  );
}

/** Top bar with a slide-over navigation sheet on small screens. */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-separator bg-surface-translucent px-4 backdrop-blur-xl backdrop-saturate-150 lg:hidden">
        <Brand />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open navigation"
          aria-expanded={open}
          className="-mr-1.5 flex size-9 items-center justify-center rounded-lg text-text-secondary hover:bg-fill"
        >
          <Menu className="size-5" />
        </button>
      </header>

      <div
        className={cn(
          "fixed inset-0 z-40 bg-black/30 transition-opacity duration-300 lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={() => setOpen(false)}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        inert={!open}
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col bg-surface shadow-raised transition-transform duration-300 ease-(--ease-standard) lg:hidden",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-4 pb-5">
          <Brand />
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
            className="-mr-1.5 flex size-9 items-center justify-center rounded-lg text-text-secondary hover:bg-fill"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3">
          <NavLinks onNavigate={() => setOpen(false)} />
        </div>
        <div className="p-4">
          <SidebarFooter />
        </div>
      </div>
    </>
  );
}
