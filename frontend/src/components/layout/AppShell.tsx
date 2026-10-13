import { MobileNav, Sidebar } from "./Navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh">
      <a
        href="#main"
        className="fixed top-3 left-3 z-[60] -translate-y-16 rounded-full bg-surface px-4 py-2 text-[13px] font-medium text-text shadow-raised transition-transform focus-visible:translate-y-0"
      >
        Skip to content
      </a>
      <Sidebar />
      <MobileNav />
      <main id="main" tabIndex={-1} className="outline-none lg:pl-64">
        <div className="mx-auto w-full max-w-6xl px-4 pt-8 pb-20 sm:px-8 sm:pt-12 lg:px-12 lg:pt-14">
          {children}
        </div>
      </main>
    </div>
  );
}
