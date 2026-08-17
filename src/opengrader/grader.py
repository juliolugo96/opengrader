"""Pass/fail grading orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from opengrader.config import AssignmentConfig
from opengrader.results import GradingResult, SubmissionResult, TestResult
from opengrader.submissions import Submission


class Runner(Protocol):
    def run(
        self,
        submission: Path,
        command: str,
        timeout_seconds: float,
        assignment: AssignmentConfig,
    ): ...


def grade_assignment(
    assignment: AssignmentConfig,
    submissions: list[Submission],
    runner: Runner,
    runner_name: str,
) -> GradingResult:
    """Grade all submissions sequentially and return their complete results."""

    submission_results: list[SubmissionResult] = []
    for submission in submissions:
        test_results: list[TestResult] = []
        for test in assignment.tests:
            command = (
                f"({assignment.setup}) && ({test.command})"
                if assignment.setup
                else test.command
            )
            execution = runner.run(
                submission=submission.path,
                command=command,
                timeout_seconds=test.timeout_seconds or assignment.timeout_seconds,
                assignment=assignment,
            )
            passed = execution.exit_code == 0 and not execution.timed_out
            test_results.append(
                TestResult(
                    name=test.name,
                    command=test.command,
                    passed=passed,
                    points_earned=test.points if passed else 0,
                    points_possible=test.points,
                    exit_code=execution.exit_code,
                    timed_out=execution.timed_out,
                    duration_seconds=execution.duration_seconds,
                    stdout=execution.stdout,
                    stderr=execution.stderr,
                )
            )
        submission_results.append(
            SubmissionResult(student_id=submission.student_id, tests=test_results)
        )

    return GradingResult(
        assignment=assignment.name,
        generated_at=datetime.now(UTC),
        runner=runner_name,
        submissions=submission_results,
    )

