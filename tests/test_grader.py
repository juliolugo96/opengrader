from pathlib import Path

from opengrader.config import AssignmentConfig
from opengrader.grader import grade_assignment
from opengrader.runners import LocalRunner
from opengrader.submissions import Submission


def test_local_grading_awards_pass_fail_points(tmp_path: Path) -> None:
    submission_path = tmp_path / "student"
    submission_path.mkdir()
    (submission_path / "answer.txt").write_text("42\n", encoding="utf-8")
    assignment = AssignmentConfig.model_validate(
        {
            "name": "Answer",
            "tests": [
                {"name": "correct", "command": "test \"$(cat answer.txt)\" = 42", "points": 4},
                {"name": "incorrect", "command": "test -f missing.txt", "points": 1},
            ],
        }
    )

    result = grade_assignment(
        assignment,
        [Submission(student_id="student", path=submission_path)],
        LocalRunner(),
        "local",
    )

    submission = result.submissions[0]
    assert submission.score == 4
    assert submission.maximum_score == 5
    assert [test.passed for test in submission.tests] == [True, False]


def test_local_grading_enforces_timeout(tmp_path: Path) -> None:
    submission_path = tmp_path / "student"
    submission_path.mkdir()
    assignment = AssignmentConfig.model_validate(
        {
            "name": "Timeout",
            "timeout_seconds": 0.05,
            "tests": [{"name": "slow", "command": "sleep 1"}],
        }
    )

    result = grade_assignment(
        assignment,
        [Submission(student_id="student", path=submission_path)],
        LocalRunner(),
        "local",
    )

    test = result.submissions[0].tests[0]
    assert test.timed_out is True
    assert test.exit_code is None
    assert test.points_earned == 0

