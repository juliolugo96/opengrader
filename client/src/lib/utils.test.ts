import { describe, expect, it } from "vitest";

import { buildResultsCsv, formatDuration, gradebookMetrics, jobDuration, percentage } from "@/lib/utils";
import type { GradingResult, Job, TestExecution } from "@/types/grader";

const passingTest = { passed: true } as TestExecution;
const failingTest = { passed: false } as TestExecution;

const result: GradingResult = {
  assignment: "Intro",
  generated_at: "2026-01-01T00:00:00Z",
  runner: "docker",
  workers: 2,
  retries: 1,
  submissions: [
    {
      student_id: "alice",
      score: 8,
      maximum_score: 10,
      passed: true,
      status: "pass",
      tests: [passingTest]
    },
    {
      student_id: "bob, jr",
      score: 2,
      maximum_score: 10,
      passed: false,
      status: "partial",
      tests: [failingTest]
    }
  ]
};

describe("result formatters", () => {
  it("formats durations across useful units", () => {
    expect(formatDuration(0.125)).toBe("125ms");
    expect(formatDuration(4.2)).toBe("4.20s");
    expect(formatDuration(82)).toBe("1m 22s");
    expect(formatDuration(null)).toBe("—");
  });

  it("calculates gradebook aggregates", () => {
    expect(gradebookMetrics(result)).toEqual({
      averagePercentage: 50,
      passRate: 50,
      studentCount: 2,
      totalScore: 10,
      maximumScore: 20
    });
    expect(percentage(1, 3)).toBe(33.3);
    expect(percentage(1, 0)).toBe(0);

    const empty = { ...result, submissions: [] };
    expect(gradebookMetrics(empty)).toEqual({
      averagePercentage: 0,
      passRate: 0,
      studentCount: 0,
      totalScore: 0,
      maximumScore: 0
    });
  });

  it("calculates completed and active job durations defensively", () => {
    const completed = {
      created_at: "2026-01-01T00:00:00Z",
      started_at: "2026-01-01T00:00:02Z",
      completed_at: "2026-01-01T00:00:07Z"
    } as Job;

    expect(jobDuration(completed)).toBe(5);
    expect(jobDuration({ ...completed, started_at: null }, Date.parse("2026-01-01T00:00:10Z"))).toBe(7);
    expect(jobDuration({ ...completed, started_at: "invalid" })).toBeNull();
    expect(jobDuration({ ...completed, completed_at: "2025-12-31T23:59:00Z" })).toBe(0);
  });

  it("exports spreadsheet-safe CSV", () => {
    const csv = buildResultsCsv(result);
    expect(csv).toBe(
      "submission,score,maximum_score,percentage,status,tests_passed,tests_total\n" +
      "alice,8,10,80,pass,1,1\n" +
      '"bob, jr",2,10,20,partial,0,1\n'
    );
  });

  it("neutralizes spreadsheet formulas in student identifiers", () => {
    const unsafe = structuredClone(result);
    unsafe.submissions[0].student_id = "=IMPORTXML(example)";
    expect(buildResultsCsv(unsafe)).toContain("'=IMPORTXML(example)");
  });
});
