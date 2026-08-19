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
  statistics: ResultStatistics;
}

export interface ResultStatistics {
  total_score: number;
  maximum_points: number;
  student_count: number;
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

export type PdfSubmissionStatus = "draft" | "finalized";

export interface RubricCriterion {
  id: string;
  title: string;
  description: string;
  max_points: number;
}

export interface RubricScore {
  criterion_id: string;
  points: number;
  feedback: string;
}

export interface PdfAnnotation {
  id?: string;
  page: number;
  x: number;
  y: number;
  comment: string;
}

export interface PdfGradeRequest {
  rubric: RubricCriterion[];
  scores: RubricScore[];
  annotations: PdfAnnotation[];
  overall_feedback: string;
  finalized: boolean;
}

export interface PdfSubmission {
  id: string;
  assignment_id: string | null;
  student_id: string;
  title: string;
  original_filename: string;
  size_bytes: number;
  sha256: string;
  page_count: number;
  status: PdfSubmissionStatus;
  grade: PdfGradeRequest | null;
  total_score: number;
  maximum_points: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
}

export interface PdfUploadInput {
  file: File;
  studentId: string;
  title: string;
  assignmentId?: string;
}

export type AppLocale = "en" | "es" | "zh-CN";
export type AcademicAssignmentKind = "automated" | "pdf";

export interface AcademicContext {
  institution: string;
  course_code: string;
  course_name: string;
  period: string;
  section: string;
}

export interface AssignmentCheck {
  name: string;
  command: string;
  points: number;
  timeout_seconds?: number | null;
  partial_credit?: Record<number, number>;
}

export interface AutomatedAssignmentDefinition {
  image: string;
  setup: string | null;
  timeout_seconds: number;
  memory_mb: number;
  cpus: number;
  pids_limit: number;
  tests: AssignmentCheck[];
}

export interface AcademicAssignmentInput {
  name: string;
  kind: AcademicAssignmentKind;
  context: AcademicContext;
  automated: AutomatedAssignmentDefinition | null;
}

export interface AcademicAssignment extends AcademicAssignmentInput {
  id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AssignmentLaunchInput {
  submissionsDirectory: string;
  workers: number;
  retries: number;
  submissionPatterns: string[];
  noDocker: boolean;
}

export type SubscriptionStatus =
  | "none"
  | "incomplete"
  | "incomplete_expired"
  | "trialing"
  | "active"
  | "past_due"
  | "canceled"
  | "unpaid"
  | "paused";

export interface BillingUsageSummary {
  total_units: number;
  reported_units: number;
  pending_units: number;
}

export interface BillingOverview {
  mode: "local" | "hosted";
  status: SubscriptionStatus;
  entitled: boolean;
  customer_configured: boolean;
  subscription_configured: boolean;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  usage: BillingUsageSummary;
}

export interface BillingSessionResponse {
  url: string;
}
