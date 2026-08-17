from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import UTC
from pathlib import Path

import pytest

from opengrader.config import AssignmentConfig, TestConfig as GraderTestConfig
from opengrader.grader import credit_for, grade_assignment
from opengrader.runners import ExecutionResult
from opengrader.submissions import Submission

pytestmark = pytest.mark.unit


def execution(exit_code: int | None, *, timed_out: bool = False) -> ExecutionResult:
    return ExecutionResult(
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration_seconds=0.01,
        timed_out=timed_out,
    )


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (execution(0), 1.0),
        (execution(2), 0.5),
        (execution(7), 0.0),
        (execution(None, timed_out=True), 0.0),
        (execution(2, timed_out=True), 0.0),
    ],
)
def test_credit_for_exit_outcome(outcome: ExecutionResult, expected: float) -> None:
    test = GraderTestConfig(
        name="rubric", command="grade", points=5, partial_credit={2: 0.5}
    )

    assert credit_for(test, outcome) == expected


class SequenceRunner:
    def __init__(self, outcomes: dict[str, list[ExecutionResult]]) -> None:
        self.outcomes = outcomes
        self.calls: defaultdict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def run(self, submission, command, timeout_seconds, assignment):
        del command, timeout_seconds, assignment
        with self._lock:
            index = self.calls[submission.name]
            self.calls[submission.name] += 1
        return self.outcomes[submission.name][index]


def test_retries_keep_best_attempt_and_stop_at_full_credit(tmp_path: Path) -> None:
    assignment = AssignmentConfig(
        name="Retry",
        tests=[
            GraderTestConfig(
                name="rubric", command="grade", points=10, partial_credit={2: 0.5}
            )
        ],
    )
    paths = [tmp_path / name for name in ("partial", "eventual")]
    for path in paths:
        path.mkdir()
    runner = SequenceRunner(
        {
            "partial": [execution(2), execution(1), execution(2)],
            "eventual": [execution(1), execution(0)],
        }
    )

    result = grade_assignment(
        assignment,
        [Submission(path.name, path) for path in paths],
        runner,
        "fake",
        retries=2,
    )

    partial, eventual = result.submissions
    assert partial.score == 5
    assert partial.tests[0].attempts == 3
    assert partial.tests[0].exit_code == 2
    assert eventual.score == 10
    assert eventual.tests[0].attempts == 2
    assert runner.calls == {"partial": 3, "eventual": 2}


class DelayedRunner:
    def __init__(self) -> None:
        self.active = 0
        self.peak_active = 0
        self._lock = threading.Lock()

    def run(self, submission, command, timeout_seconds, assignment):
        del command, timeout_seconds, assignment
        with self._lock:
            self.active += 1
            self.peak_active = max(self.peak_active, self.active)
        time.sleep(0.03)
        with self._lock:
            self.active -= 1
        return execution(0)


def test_parallel_grading_preserves_input_order(tmp_path: Path) -> None:
    assignment = AssignmentConfig(name="Parallel", tests=[{"name": "ok", "command": "true"}])
    submissions = []
    for name in ("a", "b", "c"):
        path = tmp_path / name
        path.mkdir()
        submissions.append(Submission(name, path))

    runner = DelayedRunner()
    result = grade_assignment(assignment, submissions, runner, "fake", workers=3)

    assert [item.student_id for item in result.submissions] == ["a", "b", "c"]
    assert result.workers == 3
    assert runner.peak_active == 3


def test_worker_limit_is_respected(tmp_path: Path) -> None:
    assignment = AssignmentConfig(name="Limit", tests=[{"name": "ok", "command": "true"}])
    submissions = []
    for name in ("a", "b", "c", "d"):
        path = tmp_path / name
        path.mkdir()
        submissions.append(Submission(name, path))
    runner = DelayedRunner()

    grade_assignment(assignment, submissions, runner, "fake", workers=2)

    assert runner.peak_active == 2


def test_defaults_are_single_worker_without_retries(tmp_path: Path) -> None:
    path = tmp_path / "student"
    path.mkdir()
    assignment = AssignmentConfig(name="Defaults", tests=[{"name": "fail", "command": "false"}])
    runner = SequenceRunner({"student": [execution(1)]})

    result = grade_assignment(
        assignment, [Submission("student", path)], runner, "fake"
    )

    assert result.workers == 1
    assert result.retries == 0
    assert result.generated_at.tzinfo is UTC
    assert result.submissions[0].tests[0].attempts == 1
    assert runner.calls == {"student": 1}


class RecordingRunner:
    def __init__(self, outcomes: list[ExecutionResult]) -> None:
        self.outcomes = iter(outcomes)
        self.calls: list[dict[str, object]] = []

    def run(self, submission, command, timeout_seconds, assignment):
        self.calls.append(
            {
                "submission": submission,
                "command": command,
                "timeout_seconds": timeout_seconds,
                "assignment": assignment,
            }
        )
        return next(self.outcomes)


def test_attempt_metadata_uses_best_outcome_and_total_duration(tmp_path: Path) -> None:
    path = tmp_path / "student"
    path.mkdir()
    assignment = AssignmentConfig.model_validate(
        {
            "name": "Metadata",
            "setup": "prepare",
            "timeout_seconds": 30,
            "tests": [
                {
                    "name": "rubric",
                    "command": "grade",
                    "points": 5,
                    "timeout_seconds": 3,
                    "partial_credit": {2: 1 / 3},
                }
            ],
        }
    )
    first = ExecutionResult(2, "first out", "first err", 0.1)
    second = ExecutionResult(2, "second out", "second err", 0.2)
    runner = RecordingRunner([first, second])

    result = grade_assignment(
        assignment, [Submission("student", path)], runner, "fake", retries=1
    )

    test = result.submissions[0].tests[0]
    assert test.points_earned == 1.666667
    assert test.duration_seconds == pytest.approx(0.3)
    assert test.stdout == "first out"
    assert test.stderr == "first err"
    assert runner.calls == [
        {
            "submission": path,
            "command": "(prepare) && (grade)",
            "timeout_seconds": 3,
            "assignment": assignment,
        },
        {
            "submission": path,
            "command": "(prepare) && (grade)",
            "timeout_seconds": 3,
            "assignment": assignment,
        },
    ]


def test_equal_zero_credit_prefers_non_timeout_outcome(tmp_path: Path) -> None:
    path = tmp_path / "student"
    path.mkdir()
    assignment = AssignmentConfig(name="Tie", tests=[{"name": "test", "command": "grade"}])
    timeout = ExecutionResult(None, "", "timeout", 0.1, timed_out=True)
    failure = ExecutionResult(1, "", "ordinary failure", 0.1)
    runner = RecordingRunner([timeout, failure])

    result = grade_assignment(
        assignment, [Submission("student", path)], runner, "fake", retries=1
    )

    test = result.submissions[0].tests[0]
    assert test.status == "fail"
    assert test.exit_code == 1
    assert test.stderr == "ordinary failure"
    assert test.timed_out is False


@pytest.mark.parametrize("workers, retries", [(0, 0), (1, -1)])
def test_invalid_batch_options_are_rejected(
    tmp_path: Path, workers: int, retries: int
) -> None:
    assignment = AssignmentConfig(name="Invalid", tests=[{"name": "ok", "command": "true"}])

    message = "workers must be at least 1" if workers == 0 else "retries must not be negative"
    with pytest.raises(ValueError, match=f"^{message}$"):
        grade_assignment(assignment, [], DelayedRunner(), "fake", workers=workers, retries=retries)
