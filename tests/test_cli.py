import json
from pathlib import Path

from typer.testing import CliRunner

from opengrader.cli import app


def test_cli_grades_with_local_runner(tmp_path: Path) -> None:
    assignment = tmp_path / "assignment.yaml"
    assignment.write_text(
        "name: CLI test\ntests:\n  - name: exits\n    command: python solution.py\n",
        encoding="utf-8",
    )
    submissions = tmp_path / "submissions" / "student-1"
    submissions.mkdir(parents=True)
    (submissions / "solution.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    output = tmp_path / "output"

    result = CliRunner().invoke(
        app,
        ["run", str(assignment), str(submissions.parent), "--no-docker", "-o", str(output)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads((output / "results.json").read_text(encoding="utf-8"))
    assert payload["runner"] == "local"
    assert payload["submissions"][0]["passed"] is True

