import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { GradebookMetrics, GradingResult, Job } from "@/types/grader";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return "—";
  }
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}m ${remainder}s`;
}

export function jobDuration(job: Job, now = Date.now()): number | null {
  const start = job.started_at ?? job.created_at;
  const end = job.completed_at;
  const startTime = new Date(start).getTime();
  const endTime = end ? new Date(end).getTime() : now;
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) return null;
  return Math.max(0, (endTime - startTime) / 1000);
}

export function percentage(score: number, maximum: number): number {
  if (maximum <= 0) return 0;
  return Math.round((score / maximum) * 1000) / 10;
}

export function formatScore(score: number, maximum: number): string {
  return `${formatPoints(score)} / ${formatPoints(maximum)}`;
}

export function gradebookMetrics(result: GradingResult): GradebookMetrics {
  let totalScore = 0;
  let maximumScore = 0;
  let passed = 0;

  for (const submission of result.submissions) {
    totalScore += submission.score;
    maximumScore += submission.maximum_score;
    if (submission.passed) passed += 1;
  }

  const studentCount = result.submissions.length;
  return {
    averagePercentage: percentage(totalScore, maximumScore),
    passRate: studentCount === 0 ? 0 : Math.round((passed / studentCount) * 1000) / 10,
    studentCount,
    totalScore,
    maximumScore
  };
}

export function shortId(value: string, length = 8): string {
  return value.length <= length ? value : value.slice(0, length);
}

export function humanizeAction(action: string): string {
  return action.replace(/^job[._]/, "").replaceAll(/[._-]/g, " ");
}

export function buildResultsCsv(result: GradingResult): string {
  const rows = [
    ["submission", "score", "maximum_score", "percentage", "status", "tests_passed", "tests_total"],
    ...result.submissions.map((submission) => [
      submission.student_id,
      String(submission.score),
      String(submission.maximum_score),
      String(percentage(submission.score, submission.maximum_score)),
      submission.status,
      String(submission.tests.filter((test) => test.passed).length),
      String(submission.tests.length)
    ])
  ];
  return `${rows.map((row) => row.map(csvCell).join(",")).join("\n")}\n`;
}

export function downloadText(filename: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function formatPoints(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function csvCell(value: string): string {
  const safeValue = /^[=+\-@]/.test(value) ? `'${value}` : value;
  return /[",\n]/.test(safeValue) ? `"${safeValue.replaceAll('"', '""')}"` : safeValue;
}
