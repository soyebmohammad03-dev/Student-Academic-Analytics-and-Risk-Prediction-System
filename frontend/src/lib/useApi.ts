"use client";

import { useEffect, useState } from "react";

import { ApiError, request } from "./api";

export interface ApiResource<T> {
  /** Latest successful response; kept while a new path loads, so content does not jump. */
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
}

interface Settled<T> {
  key: string;
  data?: T;
  error?: ApiError;
}

/**
 * Fetch a GET endpoint and re-fetch whenever `path` (or `reloadKey`) changes. Pass
 * `null` to skip. Loading is derived from whether the last settled response is for the
 * current request, so no state is set synchronously inside the effect.
 */
export function useApi<T>(path: string | null, reloadKey = 0): ApiResource<T> {
  const [settled, setSettled] = useState<Settled<T>>();
  const [lastData, setLastData] = useState<T>();

  const key = `${reloadKey}:${path}`;

  useEffect(() => {
    if (path === null) return;
    const key = `${reloadKey}:${path}`;
    const controller = new AbortController();
    request<T>(path, { signal: controller.signal })
      .then((data) => {
        setSettled({ key, data });
        setLastData(data);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSettled({
          key,
          error: error instanceof ApiError ? error : new ApiError("Unexpected error."),
        });
      });
    return () => controller.abort();
  }, [path, reloadKey]);

  const current = settled?.key === key;
  return {
    data: current ? (settled?.data ?? lastData) : lastData,
    error: current ? settled?.error : undefined,
    loading: path !== null && !current,
  };
}
