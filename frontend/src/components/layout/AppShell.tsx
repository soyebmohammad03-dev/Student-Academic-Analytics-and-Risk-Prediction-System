import { MobileNav, Sidebar } from "./Navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh">
      <Sidebar />
      <MobileNav />
      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-5xl px-4 pt-8 pb-20 sm:px-8 sm:pt-12 lg:px-12 lg:pt-16">
          {children}
        </div>
      </main>
    </div>
  );
}
