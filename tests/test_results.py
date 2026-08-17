import json
from datetime import UTC, datetime
from pathlib import Path

from opengrader.results import (
    GradingResult,
    SubmissionResult,
    TestResult as GradedTestResult,
    write_results,
)


def test_result_scores_and_writes_both_formats(tmp_path: Path) -> None:
    result = GradingResult(
        assignment="Example",
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        runner="local",
        submissions=[
            SubmissionResult(
                student_id="student|one",
                tests=[
                    GradedTestResult(
                        name="passes",
                        command="true",
                        passed=True,
                        points_earned=2,
                        points_possible=2,
                        exit_code=0,
                        duration_seconds=0.01,
                    ),
                    GradedTestResult(
                        name="fails",
                        command="false",
                        passed=False,
                        points_earned=0,
                        points_possible=3,
                        exit_code=1,
                        duration_seconds=0.01,
                    ),
                ],
            )
        ],
    )

    json_path, markdown_path = write_results(result, tmp_path / "reports")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["submissions"][0]["score"] == 2
    assert payload["submissions"][0]["maximum_score"] == 5
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "student\\|one" in markdown
    assert "2/5" in markdown
    assert "Fail" in markdown
