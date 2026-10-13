"use client";

import { Suspense, useSyncExternalStore } from "react";

import { Skeleton } from "@/components/ui/Skeleton";

const subscribe = () => () => {};

function Placeholder() {
  return (
    <div className="space-y-6" role="status" aria-busy="true" aria-label="Loading page">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-9 w-72 max-w-full" />
      <Skeleton className="h-5 w-full max-w-xl" />
      <Skeleton className="h-64 w-full rounded-2xl" />
    </div>
  );
}

/**
 * Renders an analysis view only in the browser. Views read the shared cohort and
 * scenario from the URL and sessionStorage, which the server cannot see; rendering
 * them before mount would briefly show (and request) the defaults instead.
 */
export function ClientView({ children }: { children: React.ReactNode }) {
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  return <Suspense fallback={<Placeholder />}>{mounted ? children : <Placeholder />}</Suspense>;
}
