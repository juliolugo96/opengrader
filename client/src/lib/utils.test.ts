import { describe, expect, it } from "vitest";

import { buildResultsCsv, formatDuration, gradebookMetrics, percentage } from "@/lib/utils";
import type { GradingResult } from "@/types/grader";

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
      tests: []
    },
    {
      student_id: "bob, jr",
      score: 2,
      maximum_score: 10,
      passed: false,
      status: "partial",
      tests: []
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
  });

  it("exports spreadsheet-safe CSV", () => {
    const csv = buildResultsCsv(result);
    expect(csv).toContain('"bob, jr",2,10,20,partial,0,0');
    expect(csv.endsWith("\n")).toBe(true);
  });

  it("neutralizes spreadsheet formulas in student identifiers", () => {
    const unsafe = structuredClone(result);
    unsafe.submissions[0].student_id = "=IMPORTXML(example)";
    expect(buildResultsCsv(unsafe)).toContain("'=IMPORTXML(example)");
  });
});
