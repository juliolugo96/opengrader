import { getSettings, type AppSettings } from "@/lib/storage";
import type {
  AcademicAssignment,
  AcademicAssignmentInput,
  AssignmentLaunchInput,
  AuditEvent,
  BillingOverview,
  BillingSessionResponse,
  CreateJobInput,
  HealthResponse,
  Job,
  JobResultResponse,
  JobStatus,
  PdfGradeRequest,
  PdfSubmission,
  PdfUploadInput
} from "@/types/grader";

interface RequestOptions extends RequestInit {
  authenticated?: boolean;
  responseType?: "json" | "blob";
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

export function listAssignments(options: {
  institution?: string;
  courseCode?: string;
  period?: string;
  section?: string;
} = {}): Promise<AcademicAssignment[]> {
  const search = new URLSearchParams({ limit: "100", offset: "0" });
  if (options.institution) search.set("institution", options.institution);
  if (options.courseCode) search.set("course_code", options.courseCode);
  if (options.period) search.set("period", options.period);
  if (options.section) search.set("section", options.section);
  return apiRequest<AcademicAssignment[]>(`/v1/assignments?${search}`);
}

export function createAssignment(input: AcademicAssignmentInput): Promise<AcademicAssignment> {
  return apiRequest<AcademicAssignment>("/v1/assignments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
}

export function updateAssignment(assignmentId: string, input: AcademicAssignmentInput): Promise<AcademicAssignment> {
  return apiRequest<AcademicAssignment>(`/v1/assignments/${encodeURIComponent(assignmentId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
}

export function deleteAssignment(assignmentId: string): Promise<void> {
  return apiRequest<void>(`/v1/assignments/${encodeURIComponent(assignmentId)}`, { method: "DELETE" });
}

export function launchAssignment(assignmentId: string, input: AssignmentLaunchInput): Promise<Job> {
  return apiRequest<Job>(`/v1/assignments/${encodeURIComponent(assignmentId)}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      submissions_dir: input.submissionsDirectory.trim(),
      workers: input.workers,
      retries: input.retries,
      submission_patterns: input.submissionPatterns,
      no_docker: input.noDocker
    })
  });
}

export function getBillingOverview(): Promise<BillingOverview> {
  return apiRequest<BillingOverview>("/v1/billing/overview");
}

export function createBillingCheckout(email: string): Promise<BillingSessionResponse> {
  return apiRequest<BillingSessionResponse>("/v1/billing/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() })
  });
}

export function createBillingPortal(): Promise<BillingSessionResponse> {
  return apiRequest<BillingSessionResponse>("/v1/billing/portal", { method: "POST" });
}

export function listPdfSubmissions(options: { assignmentId?: string; limit?: number; offset?: number } = {}): Promise<PdfSubmission[]> {
  const search = new URLSearchParams({
    limit: String(options.limit ?? 100),
    offset: String(options.offset ?? 0)
  });
  if (options.assignmentId) search.set("assignment_id", options.assignmentId);
  return apiRequest<PdfSubmission[]>(`/v1/pdf-submissions?${search}`);
}

export async function listAllPdfSubmissions(): Promise<PdfSubmission[]> {
  const pageSize = 100;
  const submissions: PdfSubmission[] = [];
  let page: PdfSubmission[];
  do {
    page = await listPdfSubmissions({ limit: pageSize, offset: submissions.length });
    submissions.push(...page);
  } while (page.length === pageSize);
  return submissions;
}

export function getPdfSubmission(submissionId: string): Promise<PdfSubmission> {
  return apiRequest<PdfSubmission>(`/v1/pdf-submissions/${encodeURIComponent(submissionId)}`);
}

export function uploadPdfSubmission(input: PdfUploadInput): Promise<PdfSubmission> {
  const body = new FormData();
  body.set("student_id", input.studentId.trim());
  body.set("title", input.title.trim());
  if (input.assignmentId) body.set("assignment_id", input.assignmentId);
  body.set("file", input.file);
  return apiRequest<PdfSubmission>("/v1/pdf-submissions", { method: "POST", body });
}

export function savePdfGrade(submissionId: string, grade: PdfGradeRequest): Promise<PdfSubmission> {
  return apiRequest<PdfSubmission>(`/v1/pdf-submissions/${encodeURIComponent(submissionId)}/grade`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(grade)
  });
}

export function getPdfDocument(submissionId: string): Promise<Blob> {
  return apiRequest<Blob>(`/v1/pdf-submissions/${encodeURIComponent(submissionId)}/document`, {
    responseType: "blob"
  });
}

export function getPdfFeedback(submissionId: string): Promise<Blob> {
  return apiRequest<Blob>(`/v1/pdf-submissions/${encodeURIComponent(submissionId)}/feedback.pdf`, {
    responseType: "blob"
  });
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    authenticated = true,
    responseType,
    settings: settingsOverride,
    ...fetchOptions
  } = options;
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

  const contentType = response.headers.get("content-type");
  const payload: unknown = responseType === "blob" && response.ok
    ? await response.blob()
    : contentType?.includes("application/json")
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
