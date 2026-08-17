from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from opengrader.config import AssignmentConfig
from opengrader.grader import grade_assignment
from opengrader.results import write_results
from opengrader.runners import LocalRunner
from opengrader.submissions import discover_submissions, select_submissions

pytestmark = pytest.mark.integration


def test_discovery_local_grading_and_all_reports_work_together(tmp_path: Path) -> None:
    root = tmp_path / "submissions"
    for name, exit_code in (("zoe", 2), ("amy", 0), ("ignored", 1)):
        submission = root / name
        submission.mkdir(parents=True)
        (submission / "solution.py").write_text(
            f"raise SystemExit({exit_code})\n", encoding="utf-8"
        )
    assignment = AssignmentConfig.model_validate(
        {
            "name": "Pipeline",
            "tests": [
                {
                    "name": "rubric",
                    "command": "python solution.py",
                    "points": 4,
                    "partial_credit": {2: 0.25},
                }
            ],
        }
    )

    submissions = select_submissions(discover_submissions(root), ["amy", "z*"])
    result = grade_assignment(
        assignment, submissions, LocalRunner(), "local", workers=2, retries=1
    )
    json_path, markdown_path, csv_path = write_results(result, tmp_path / "reports")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert [(item["student_id"], item["score"]) for item in payload["submissions"]] == [
        ("amy", 4.0),
        ("zoe", 1.0),
    ]
    assert "Partial" in markdown_path.read_text(encoding="utf-8")
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0] == {
        "submission": "amy",
        "score": "4",
        "maximum_score": "4",
        "percentage": "100",
        "status": "pass",
        "tests_passed": "1",
        "tests_total": "1",
    }
    assert rows[1]["status"] == "partial"
