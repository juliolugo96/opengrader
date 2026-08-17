"""Serializable grading results and report writers."""

from __future__ import annotations

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
    duration_seconds: float = Field(ge=0)
    stdout: str = ""
    stderr: str = ""


class SubmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    tests: list[TestResult]

    @computed_field
    @property
    def score(self) -> float:
        return sum(test.points_earned for test in self.tests)

    @computed_field
    @property
    def maximum_score(self) -> float:
        return sum(test.points_possible for test in self.tests)

    @computed_field
    @property
    def passed(self) -> bool:
        return all(test.passed for test in self.tests)


class GradingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment: str
    generated_at: datetime
    runner: str
    submissions: list[SubmissionResult]


def write_results(result: GradingResult, output_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable JSON and a compact Markdown summary."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    markdown_path = output_dir / "summary.md"

    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_to_markdown(result), encoding="utf-8")
    return json_path, markdown_path


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
        status = "Pass" if submission.passed else "Fail"
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
            status = "Pass" if test.passed else ("Timeout" if test.timed_out else "Fail")
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

