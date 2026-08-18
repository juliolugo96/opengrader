export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface HealthResponse {
  status: string;
  version: string;
  authentication_configured: boolean;
}

export interface ApiJobRequest {
  assignment_file: string;
  submissions_dir: string;
  no_docker: boolean;
  workers: number;
  retries: number;
  submission_patterns: string[];
}

export interface CreateJobInput {
  assignmentPath: string;
  submissionsDirectory: string;
  workers: number;
  retries: number;
  submissionFilter: string;
  noDocker: boolean;
}

export interface Job {
  id: string;
  status: JobStatus;
  request: ApiJobRequest;
  created_by: string;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  reports: Record<string, string>;
  error: string | null;
}

export interface TestExecution {
  name: string;
  command: string;
  passed: boolean;
  status: "pass" | "partial" | "fail" | "timeout";
  points_earned: number;
  points_possible: number;
  exit_code: number | null;
  timed_out: boolean;
  attempts: number;
  duration_seconds: number;
  stdout: string;
  stderr: string;
}

export interface StudentResult {
  student_id: string;
  tests: TestExecution[];
  score: number;
  maximum_score: number;
  passed: boolean;
  status: "pass" | "partial" | "fail";
}

export interface GradingResult {
  assignment: string;
  generated_at: string;
  runner: string;
  workers: number;
  retries: number;
  submissions: StudentResult[];
}

export interface JobResultResponse {
  job_id: string;
  result: GradingResult;
  reports: Record<string, string>;
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
}

export interface GradebookMetrics {
  averagePercentage: number;
  passRate: number;
  studentCount: number;
  totalScore: number;
  maximumScore: number;
}
