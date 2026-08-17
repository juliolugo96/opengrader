from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from opengrader.cli import app

pytestmark = pytest.mark.e2e
scenarios("../features/batch_grading.feature")


@pytest.fixture
def world(tmp_path: Path) -> dict[str, object]:
    return {"root": tmp_path, "output": tmp_path / "results"}


@given("an assignment that awards half credit for exit code 2")
def assignment(world: dict[str, object]) -> None:
    root = world["root"]
    assert isinstance(root, Path)
    assignment_path = root / "assignment.yaml"
    assignment_path.write_text(
        "name: Batch exercise\n"
        "tests:\n"
        "  - name: rubric\n"
        "    command: python solution.py\n"
        "    points: 5\n"
        "    partial_credit:\n"
        "      2: 0.5\n",
        encoding="utf-8",
    )
    world["assignment"] = assignment_path


@given("submissions named alice, bob, and carol")
def submissions(world: dict[str, object]) -> None:
    root = world["root"]
    assert isinstance(root, Path)
    submissions_root = root / "submissions"
    for name, exit_code in (("alice", 2), ("bob", 0), ("carol", 1)):
        path = submissions_root / name
        path.mkdir(parents=True)
        (path / "solution.py").write_text(
            f"raise SystemExit({exit_code})\n", encoding="utf-8"
        )
    world["submissions"] = submissions_root


@when("I grade alice and bob with 2 workers and 1 retry")
def grade_selected(world: dict[str, object]) -> None:
    world["result"] = _invoke(
        world,
        "--submission",
        "a*",
        "--submission",
        "bob",
        "--workers",
        "2",
        "--retries",
        "1",
    )


@when(parsers.parse("I grade the unmatched pattern {pattern}"))
def grade_unmatched(world: dict[str, object], pattern: str) -> None:
    world["result"] = _invoke(world, "--submission", pattern)


@then("the command succeeds")
def command_succeeds(world: dict[str, object]) -> None:
    result = world["result"]
    assert result.exit_code == 0, result.output


@then("the JSON submissions are ordered alice then bob")
def ordered_json(world: dict[str, object]) -> None:
    payload = _json_report(world)
    assert [item["student_id"] for item in payload["submissions"]] == ["alice", "bob"]
    assert payload["workers"] == 2
    assert payload["retries"] == 1


@then("alice earns 2.5 out of 5 points after 2 attempts")
def alice_partial(world: dict[str, object]) -> None:
    alice = _json_report(world)["submissions"][0]
    assert alice["score"] == 2.5
    assert alice["maximum_score"] == 5
    assert alice["status"] == "partial"
    assert alice["tests"][0]["attempts"] == 2


@then("bob earns 5 out of 5 points after 1 attempt")
def bob_passes(world: dict[str, object]) -> None:
    bob = _json_report(world)["submissions"][1]
    assert bob["score"] == 5
    assert bob["status"] == "pass"
    assert bob["tests"][0]["attempts"] == 1


@then("the CSV report contains alice and bob but not carol")
def csv_is_filtered(world: dict[str, object]) -> None:
    output = world["output"]
    assert isinstance(output, Path)
    with (output / "results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["submission"] for row in rows] == ["alice", "bob"]


@then("the command fails with an unmatched pattern error")
def unmatched_error(world: dict[str, object]) -> None:
    result = world["result"]
    assert result.exit_code == 2
    assert "matched no submissions" in result.output


def _invoke(world: dict[str, object], *options: str):
    assignment_path = world["assignment"]
    submissions_root = world["submissions"]
    output = world["output"]
    assert isinstance(assignment_path, Path)
    assert isinstance(submissions_root, Path)
    assert isinstance(output, Path)
    return CliRunner().invoke(
        app,
        [
            "run",
            str(assignment_path),
            str(submissions_root),
            "--no-docker",
            "--output-dir",
            str(output),
            *options,
        ],
    )


def _json_report(world: dict[str, object]) -> dict:
    output = world["output"]
    assert isinstance(output, Path)
    return json.loads((output / "results.json").read_text(encoding="utf-8"))
