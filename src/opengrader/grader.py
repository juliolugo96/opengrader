"""Deterministic batch grading and scoring orchestration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from opengrader.config import AssignmentConfig, TestConfig
from opengrader.results import GradingResult, SubmissionResult, TestResult
from opengrader.runners import ExecutionResult
from opengrader.submissions import Submission


class Runner(Protocol):
    def run(
        self,
        submission: Path,
        command: str,
        timeout_seconds: float,
        assignment: AssignmentConfig,
    ) -> ExecutionResult: ...


def grade_assignment(
    assignment: AssignmentConfig,
    submissions: list[Submission],
    runner: Runner,
    runner_name: str,
    *,
    workers: int = 1,
    retries: int = 0,
) -> GradingResult:
    """Grade submissions concurrently while preserving their input order."""

    if workers < 1:
        raise ValueError("workers must be at least 1")
    if retries < 0:
        raise ValueError("retries must not be negative")

    def grade_one(submission: Submission) -> SubmissionResult:
        return _grade_submission(assignment, submission, runner, retries)

    if workers == 1:
        submission_results = [grade_one(submission) for submission in submissions]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            submission_results = list(executor.map(grade_one, submissions))

    return GradingResult(
        assignment=assignment.name,
        generated_at=datetime.now(UTC),
        runner=runner_name,
        workers=workers,
        retries=retries,
        submissions=submission_results,
    )


def credit_for(test: TestConfig, execution: ExecutionResult) -> float:
    """Return the earned fraction for one execution outcome."""

    if execution.timed_out or execution.exit_code is None:
        return 0.0
    if execution.exit_code == 0:
        return 1.0
    return test.partial_credit.get(execution.exit_code, 0.0)


def _grade_submission(
    assignment: AssignmentConfig,
    submission: Submission,
    runner: Runner,
    retries: int,
) -> SubmissionResult:
    test_results = [
        _grade_test(assignment, submission, test, runner, retries)
        for test in assignment.tests
    ]
    return SubmissionResult(student_id=submission.student_id, tests=test_results)


def _grade_test(
    assignment: AssignmentConfig,
    submission: Submission,
    test: TestConfig,
    runner: Runner,
    retries: int,
) -> TestResult:
    command = (
        f"({assignment.setup}) && ({test.command})"
        if assignment.setup
        else test.command
    )
    executions: list[ExecutionResult] = []

    for _ in range(retries + 1):
        execution = runner.run(
            submission=submission.path,
            command=command,
            timeout_seconds=test.timeout_seconds or assignment.timeout_seconds,
            assignment=assignment,
        )
        executions.append(execution)
        if credit_for(test, execution) == 1:
            break

    best_execution = max(
        executions,
        key=lambda outcome: (credit_for(test, outcome), not outcome.timed_out),
    )
    best_credit = credit_for(test, best_execution)

    return TestResult(
        name=test.name,
        command=test.command,
        passed=best_credit == 1,
        points_earned=round(test.points * best_credit, 6),
        points_possible=test.points,
        exit_code=best_execution.exit_code,
        timed_out=best_execution.timed_out,
        attempts=len(executions),
        duration_seconds=sum(outcome.duration_seconds for outcome in executions),
        stdout=best_execution.stdout,
        stderr=best_execution.stderr,
    )
