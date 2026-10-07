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

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("The analytics API is unreachable.");
  }
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed.`, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  health: (init?: RequestInit) => request<HealthResponse>("/health", init),
  project: (init?: RequestInit) => request<ProjectInfo>("/project", init),
};
