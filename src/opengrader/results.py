"""Serializable grading results and report writers."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    command: str
    passed: bool
    points_earned: float = Field(ge=0)
    points_possible: float = Field(gt=0)
    exit_code: int | None
    timed_out: bool = False
    attempts: int = Field(default=1, ge=1)
    duration_seconds: float = Field(ge=0)
    stdout: str = ""
    stderr: str = ""

    @computed_field
    @property
    def status(self) -> str:
        if self.timed_out:
            return "timeout"
        if self.passed:
            return "pass"
        if self.points_earned > 0:
            return "partial"
        return "fail"


class SubmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    tests: list[TestResult]

    @computed_field
    @property
    def score(self) -> float:
        return round(sum(test.points_earned for test in self.tests), 6)

    @computed_field
    @property
    def maximum_score(self) -> float:
        return round(sum(test.points_possible for test in self.tests), 6)

    @computed_field
    @property
    def passed(self) -> bool:
        return all(test.passed for test in self.tests)

    @computed_field
    @property
    def status(self) -> str:
        if self.passed:
            return "pass"
        if self.score > 0:
            return "partial"
        return "fail"


class GradingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment: str
    generated_at: datetime
    runner: str
    workers: int = Field(default=1, ge=1)
    retries: int = Field(default=0, ge=0)
    submissions: list[SubmissionResult]


def write_results(result: GradingResult, output_dir: Path) -> tuple[Path, Path, Path]:
    """Write JSON, Markdown, and submission-level CSV reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    markdown_path = output_dir / "summary.md"
    csv_path = output_dir / "results.csv"

    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_to_markdown(result), encoding="utf-8")
    _write_csv(result, csv_path)
    return json_path, markdown_path, csv_path


def _write_csv(result: GradingResult, path: Path) -> None:
    columns = [
        "submission",
        "score",
        "maximum_score",
        "percentage",
        "status",
        "tests_passed",
        "tests_total",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for submission in result.submissions:
            percentage = round(
                submission.score / submission.maximum_score * 100,
                6,
            )
            writer.writerow(
                {
                    "submission": submission.student_id,
                    "score": f"{submission.score:g}",
                    "maximum_score": f"{submission.maximum_score:g}",
                    "percentage": f"{percentage:g}",
                    "status": submission.status,
                    "tests_passed": sum(test.passed for test in submission.tests),
                    "tests_total": len(submission.tests),
                }
            )


def _to_markdown(result: GradingResult) -> str:
    lines = [
        f"# {_escape_heading(result.assignment)} results",
        "",
        f"Generated: {result.generated_at.isoformat()}",
        f"Runner: {result.runner}",
        "",
        "| Submission | Score | Status |",
        "| --- | ---: | :---: |",
    ]
    for submission in result.submissions:
        status = submission.status.title()
        lines.append(
            f"| {_escape_cell(submission.student_id)} | "
            f"{submission.score:g}/{submission.maximum_score:g} | {status} |"
        )

    for submission in result.submissions:
        lines.extend(
            [
                "",
                f"## {_escape_heading(submission.student_id)}",
                "",
                "| Test | Score | Status |",
                "| --- | ---: | :---: |",
            ]
        )
        for test in submission.tests:
            status = test.status.title()
            lines.append(
                f"| {_escape_cell(test.name)} | "
                f"{test.points_earned:g}/{test.points_possible:g} | {status} |"
            )
    lines.append("")
    return "\n".join(lines)


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _escape_heading(value: str) -> str:
    return value.replace("\n", " ").strip()
