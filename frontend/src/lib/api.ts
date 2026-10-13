/** Typed client for the FastAPI backend. Types mirror backend/app/schemas. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

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

// --- System (Phase 7) ---------------------------------------------------------

export type ComponentState = "available" | "unavailable" | "degraded";

export interface ComponentStatus {
  key: "api" | "dataset" | "statistics" | "models" | "interpretability";
  label: string;
  status: ComponentState;
  detail: string;
  /** Command that fixes the component, when one exists. */
  action: string | null;
}

export interface Readiness {
  status: "ready" | "degraded";
  components: ComponentStatus[];
}

export interface WilsonInterval {
  low: number | null;
  high: number | null;
  confidence: number;
}

/** Observed in the historical data; never a prediction. */
export interface ObservedRisk {
  kind: "observed_historical";
  definition: string;
  n: number;
  at_risk: number;
  percent: number;
  ci: WilsonInterval;
}

export interface CohortOverview {
  cohort: Cohort;
  subject: string;
  rows: number;
  columns: number;
  validation_status: CheckStatus;
  missing_values: number;
  duplicate_rows: number;
  invalid_values: number;
  final_grade: {
    n: number;
    mean: number | null;
    median: number | null;
    std: number | null;
    minimum: number | null;
    maximum: number | null;
    zero_count: number;
  };
  observed_risk: ObservedRisk;
}

export interface SelectedModelSummary {
  kind: "model_evaluation";
  cohort: Cohort;
  task: "regression" | "classification";
  scenario: "early" | "mid_year" | "full_history";
  model: string;
  label: string;
  /** Primary metric: "rmse" (regression) or "f1" (classification). */
  metric: string;
  cv_mean: number | null;
  cv_std: number | null;
  test: number | null;
}

export interface DashboardSummary {
  status: "ready" | "degraded";
  components: ComponentStatus[];
  dataset: { available: boolean; detail: string; cohorts: CohortOverview[] };
  models: {
    available: boolean;
    detail: string;
    trained_at: string | null;
    selected: SelectedModelSummary[];
  };
  notes: string[];
}

export interface PipelineSummary {
  cohort: Cohort;
  scenario: "early" | "mid_year" | "full_history";
  steps: Array<{ step: string; status: ComponentState; detail: string }>;
  overview: CohortOverview | null;
  scenario_features: string[];
  research_questions: Array<{
    key: string;
    evidence: "confirmatory" | "exploratory";
    p_adjusted: number | null;
    significant: boolean;
    effect: {
      name: string;
      value: number | null;
      ci: WilsonInterval | null;
      magnitude: string;
    } | null;
  }>;
  eda_charts: Record<string, number>;
  selected_models: SelectedModelSummary[];
  top_attributes: Record<string, string[]>;
  risk_profile_highlights: string[];
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

/** Build `path?key=value…` from defined parameters, in a stable order. */
export function withQuery(path: string, params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}
