import { getSettings, type AppSettings } from "@/lib/storage";
import type {
  AuditEvent,
  CreateJobInput,
  HealthResponse,
  Job,
  JobResultResponse,
  JobStatus
} from "@/types/grader";

interface RequestOptions extends RequestInit {
  authenticated?: boolean;
  settings?: AppSettings;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function testConnection(settings?: AppSettings): Promise<HealthResponse> {
  const health = await apiRequest<HealthResponse>("/health", { authenticated: false, settings });
  await apiRequest<Job[]>("/v1/jobs?limit=1", { settings });
  return health;
}

export function listJobs(options: { status?: JobStatus; limit?: number; offset?: number } = {}): Promise<Job[]> {
  const search = new URLSearchParams();
  if (options.status) search.set("status", options.status);
  search.set("limit", String(options.limit ?? 100));
  search.set("offset", String(options.offset ?? 0));
  return apiRequest<Job[]>(`/v1/jobs?${search}`);
}

export async function listAllJobs(): Promise<Job[]> {
  const pageSize = 100;
  const jobs: Job[] = [];
  let page: Job[];
  do {
    page = await listJobs({ limit: pageSize, offset: jobs.length });
    jobs.push(...page);
  } while (page.length === pageSize);
  return jobs;
}

export function getJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/v1/jobs/${encodeURIComponent(jobId)}`);
}

export function getJobResult(jobId: string): Promise<JobResultResponse> {
  return apiRequest<JobResultResponse>(`/v1/jobs/${encodeURIComponent(jobId)}/result`);
}

export function listAuditEvents(limit = 500): Promise<AuditEvent[]> {
  return apiRequest<AuditEvent[]>(`/v1/audit-events?limit=${limit}`);
}

export function createJob(input: CreateJobInput): Promise<Job> {
  return apiRequest<Job>("/v1/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assignment_path: input.assignmentPath,
      submissions_dir: input.submissionsDirectory,
      workers: input.workers,
      retries: input.retries,
      submission_filter: input.submissionFilter.trim(),
      no_docker: input.noDocker
    })
  });
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { authenticated = true, settings: settingsOverride, ...fetchOptions } = options;
  const settings = settingsOverride ?? getSettings();
  const headers = new Headers(fetchOptions.headers);
  headers.set("X-OpenGrader-Base-URL", settings.apiBaseUrl);
  if (authenticated && settings.apiKey) {
    headers.set("Authorization", `Bearer ${settings.apiKey}`);
  }

  let response: Response;
  try {
    response = await fetch(`/api/opengrader${path}`, {
      ...fetchOptions,
      headers,
      cache: "no-store"
    });
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : "Could not reach OpenGrader",
      0
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = extractErrorMessage(payload) ?? `OpenGrader returned ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }
  return payload as T;
}

function extractErrorMessage(payload: unknown): string | null {
  if (typeof payload === "string" && payload) return payload;
  if (!payload || typeof payload !== "object") return null;
  const detail = "detail" in payload ? payload.detail : null;
  if (typeof detail === "string") return detail;
  return detail ? JSON.stringify(detail) : null;
}
