import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GradebookSummary } from "@/components/results/GradebookSummary";
import type { GradingResult, Job, ResultStatistics } from "@/types/grader";

const job = {
  id: "job-1",
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:05Z"
} as Job;

const result: GradingResult = {
  assignment: "Homework 1",
  generated_at: "2026-01-01T00:00:05Z",
  runner: "local",
  workers: 2,
  retries: 0,
  submissions: [
    { student_id: "alice", score: 8, maximum_score: 10, passed: true, status: "pass", tests: [] },
    { student_id: "bob", score: 4, maximum_score: 10, passed: false, status: "partial", tests: [] }
  ]
};

const statistics: ResultStatistics = {
  total_score: 12,
  maximum_points: 20,
  student_count: 2
};

describe("GradebookSummary", () => {
  it("shows returned aggregate points alongside the computed summary", () => {
    render(<GradebookSummary job={job} result={result} statistics={statistics} />);

    expect(screen.getByText("12 / 20 cohort points")).toBeVisible();
    expect(screen.getByText("60%")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
  });
});
