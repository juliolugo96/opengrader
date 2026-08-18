from datetime import UTC, datetime

import pytest

from opengrader.mvp4_contract import (
    cohort_totals,
    normalize_job_request_payload,
    validate_job_page,
)
from opengrader.results import GradingResult, SubmissionResult, TestResult as GraderTestResult

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"assignment_path": "new.yaml", "assignment_file": "old.yaml"},
            "use either assignment_path or assignment_file, not both",
        ),
        (
            {"submission_filter": "a-*", "submission_patterns": ["b-*"]},
            "use either submission_filter or submission_patterns, not both",
        ),
    ],
)
def test_request_aliases_reject_ambiguous_payloads(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        normalize_job_request_payload(payload)


def test_cohort_totals_are_rounded_to_six_decimal_places() -> None:
    result = GradingResult(
        assignment="Precise totals",
        generated_at=datetime.now(UTC),
        runner="local",
        submissions=[
            SubmissionResult(
                student_id="student-1",
                tests=[
                    GraderTestResult(
                        name="precision",
                        command="true",
                        passed=True,
                        points_earned=0.1234567,
                        points_possible=0.7654321,
                        exit_code=0,
                        duration_seconds=0.01,
                    )
                ],
            )
        ],
    )

    assert cohort_totals(result) == (0.123457, 0.765432, 1)


@pytest.mark.parametrize("limit", [1, 100])
def test_job_page_accepts_inclusive_limit_boundaries(limit: int) -> None:
    assert validate_job_page(limit=limit, offset=0) is None


@pytest.mark.parametrize("limit", [0, 101])
def test_job_page_rejects_out_of_range_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="^limit must be between 1 and 100$"):
        validate_job_page(limit=limit, offset=0)


def test_job_page_rejects_negative_offsets() -> None:
    with pytest.raises(ValueError, match="^offset must be non-negative$"):
        validate_job_page(limit=20, offset=-1)
