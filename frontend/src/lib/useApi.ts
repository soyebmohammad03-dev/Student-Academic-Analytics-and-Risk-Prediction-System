"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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

function asApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError("Unexpected error.");
}

/**
 * Fetch a GET endpoint and re-fetch whenever `path` (or `reloadKey`) changes. Pass
 * `null` to skip. Loading is derived from whether the last settled response is for the
 * current request, so no state is set synchronously inside the effect. The previous
 * request is aborted, so a slow stale response can never overwrite a newer one.
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
        setSettled({ key, error: asApiError(error) });
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

export type PostState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: ApiError };

/**
 * POST on demand (`run`). Starting a new request aborts the previous one, and a
 * response that arrives after `reset` or a newer `run` is discarded.
 */
export function usePost<TBody, TResult>(
  path: string,
): [PostState<TResult>, (body: TBody) => void, () => void] {
  const [state, setState] = useState<PostState<TResult>>({ status: "idle" });
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const run = useCallback(
    (body: TBody) => {
      controller.current?.abort();
      const current = new AbortController();
      controller.current = current;
      setState({ status: "loading" });
      request<TResult>(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: current.signal,
      })
        .then((data) => {
          if (!current.signal.aborted) setState({ status: "success", data });
        })
        .catch((error: unknown) => {
          if (!current.signal.aborted) setState({ status: "error", error: asApiError(error) });
        });
    },
    [path],
  );

  const reset = useCallback(() => {
    controller.current?.abort();
    controller.current = null;
    setState({ status: "idle" });
  }, []);

  return [state, run, reset];
}

/**
 * POST whose body is derived from state, re-sent whenever the body changes (like
 * `useApi` for GET). Pass `null` to skip. Superseded requests are aborted and their
 * responses ignored, so results always belong to the current inputs.
 */
export function useApiPost<T>(path: string, body: unknown, reloadKey = 0): ApiResource<T> {
  const serialised = body === null ? null : JSON.stringify(body);
  const [settled, setSettled] = useState<Settled<T>>();
  const key = `${reloadKey}:${path}:${serialised}`;

  useEffect(() => {
    if (serialised === null) return;
    const key = `${reloadKey}:${path}:${serialised}`;
    const controller = new AbortController();
    request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: serialised,
      signal: controller.signal,
    })
      .then((data) => setSettled({ key, data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSettled({ key, error: asApiError(error) });
      });
    return () => controller.abort();
  }, [path, serialised, reloadKey]);

  const current = settled?.key === key;
  return {
    data: current ? settled?.data : undefined,
    error: current ? settled?.error : undefined,
    loading: serialised !== null && !current,
  };
}
