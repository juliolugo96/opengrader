import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { StudentResultCard } from "@/components/results/StudentResultCard";
import type { StudentResult } from "@/types/grader";

const student: StudentResult = {
  student_id: "alice",
  score: 0,
  maximum_score: 5,
  passed: false,
  status: "fail",
  tests: [{
    name: "slow test",
    command: "pytest -q",
    passed: false,
    status: "timeout",
    points_earned: 0,
    points_possible: 5,
    exit_code: 124,
    timed_out: true,
    attempts: 1,
    duration_seconds: 30,
    stdout: "",
    stderr: "timed out"
  }]
};

describe("StudentResultCard", () => {
  it("renders explicit exit-code and timeout badges", async () => {
    const user = userEvent.setup();
    render(<StudentResultCard student={student} />);
    await user.click(screen.getByText("slow test"));

    expect(screen.getByLabelText("Exit code 124")).toBeVisible();
    expect(screen.getByLabelText("Test timed out")).toBeVisible();
  });
});
