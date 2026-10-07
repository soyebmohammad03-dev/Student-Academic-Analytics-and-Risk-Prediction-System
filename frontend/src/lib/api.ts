/** Typed client for the FastAPI backend. Types mirror backend/app/schemas. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

export interface HealthResponse {
  status: "ok";
  version: string;
  environment: string;
}

export interface ProjectInfo {
  name: string;
  version: string;
  dataset: {
    name: string;
    source_url: string;
    available_locally: boolean;
  };
  modules: Array<{
    key: string;
    name: string;
    phase: number;
    status: "planned" | "in_progress" | "available";
  }>;
}

// --- Dataset ------------------------------------------------------------------

export type Cohort = "math" | "portuguese";
export type CheckStatus = "pass" | "warning" | "fail";
export type CellValue = string | number | null;

export interface DatasetSummary {
  cohort: Cohort;
  subject: string;
  filename: string;
  source: { name: string; url: string; license: string; citation: string };
  rows: number;
  columns: number;
  numerical_columns: number;
  categorical_columns: number;
  missing_values: number;
  duplicate_rows: number;
  invalid_values: number;
  validation_status: CheckStatus;
  target: {
    name: string;
    label: string;
    description: string;
    minimum: number;
    maximum: number;
    pass_mark: number;
    prior_grades: string[];
  };
}

export interface ColumnInfo {
  name: string;
  position: number;
  label: string;
  description: string;
  group: string;
  measure: "categorical" | "numerical";
  scale: "binary" | "nominal" | "ordinal" | "count" | "grade";
  role: "feature" | "prior_grade" | "target";
  dtype: "string" | "integer";
  allowed_values: Array<{ code: string | number; label: string }>;
  minimum: number | null;
  maximum: number | null;
  notes: string[];
  observed: {
    missing: number;
    invalid: number;
    unique: number;
    minimum: number | null;
    maximum: number | null;
  } | null;
}

export interface DatasetSchema {
  cohort: Cohort;
  source: string;
  columns: ColumnInfo[];
}

export interface DatasetQuality {
  cohort: Cohort;
  status: CheckStatus;
  rows: number;
  columns: number;
  missing_values: number;
  duplicate_rows: number;
  invalid_values: number;
  checks: Array<{
    key: string;
    title: string;
    status: CheckStatus;
    summary: string;
    affected: number;
  }>;
  observations: Array<{ key: string; title: string; detail: string; count: number }>;
  column_issues: Array<{
    name: string;
    missing: number;
    invalid: number;
    invalid_examples: string[];
  }>;
}

export interface DatasetRecords {
  cohort: Cohort;
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  search: string | null;
  columns: string[];
  items: Array<{ row: number; values: Record<string, CellValue> }>;
}

export interface CohortOverlap {
  method: string;
  match_attributes: string[];
  math_rows: number;
  portuguese_rows: number;
  join_pairs: number;
  math_rows_matched: number;
  portuguese_rows_matched: number;
  unambiguous_matches: number;
  ambiguous_profiles: number;
  caveat: string;
}

// --- Transport ----------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    message: string,
    /** HTTP status; undefined when the API could not be reached at all. */
    readonly status?: number,
    /** Machine-readable error code from the API body, e.g. "dataset_unavailable". */
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("The analytics API is unreachable.");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      code?: string;
      detail?: string;
    } | null;
    throw new ApiError(body?.detail ?? `Request to ${path} failed.`, response.status, body?.code);
  }
  return (await response.json()) as T;
}

export function datasetPath(resource: "summary" | "schema" | "quality", cohort: Cohort): string;
export function datasetPath(
  resource: "records",
  cohort: Cohort,
  options: { page: number; pageSize: number; search?: string },
): string;
export function datasetPath(
  resource: "summary" | "schema" | "quality" | "records",
  cohort: Cohort,
  options?: { page: number; pageSize: number; search?: string },
): string {
  const params = new URLSearchParams({ cohort });
  if (options) {
    params.set("page", String(options.page));
    params.set("page_size", String(options.pageSize));
    if (options.search) params.set("search", options.search);
  }
  return `/dataset/${resource}?${params}`;
}

export const api = {
  health: (init?: RequestInit) => request<HealthResponse>("/health", init),
  project: (init?: RequestInit) => request<ProjectInfo>("/project", init),
};
