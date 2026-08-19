from pathlib import Path

import pytest

from opengrader.config import load_assignment
from opengrader.grader import grade_assignment
from opengrader.results import GradingResult
from opengrader.runners import LocalRunner
from opengrader.submissions import Submission

EXAMPLE_SCORES = {
    "c-program.yaml": 10,
    "custom-rubric-image.yaml": 10,
    "java-program.yaml": 10,
    "javascript-module.yaml": 10,
    "minimal-python.yaml": 1,
    "python-cli.yaml": 10,
    "python-library.yaml": 10,
    "shell-script.yaml": 10,
    "sql-query.yaml": 10,
    "static-web-page.yaml": 10,
}


@pytest.mark.parametrize("filename, maximum_score", EXAMPLE_SCORES.items())
@pytest.mark.unit
def test_assignment_gallery_is_schema_valid(
    filename: str, maximum_score: int
) -> None:
    path = Path("examples/assignments") / filename

    assignment = load_assignment(path)

    assert assignment.maximum_score == maximum_score
    assert assignment.tests


def _grade_example(
    tmp_path: Path, filename: str, files: dict[str, str]
) -> GradingResult:
    submission_path = tmp_path / "student"
    submission_path.mkdir()
    for relative_path, content in files.items():
        (submission_path / relative_path).write_text(content, encoding="utf-8")
    assignment = load_assignment(Path("examples/assignments") / filename)

    return grade_assignment(
        assignment,
        [Submission(student_id="student", path=submission_path)],
        LocalRunner(),
        "local",
    )


@pytest.mark.integration
def test_minimal_gallery_assignment_runs_with_all_defaults(tmp_path: Path) -> None:
    result = _grade_example(
        tmp_path,
        "minimal-python.yaml",
        {"solution.py": "print('hello from OpenGrader')\n"},
    )

    assert result.submissions[0].score == 1
    assert result.submissions[0].passed is True


@pytest.mark.integration
def test_python_library_example_runs_a_complete_submission(tmp_path: Path) -> None:
    result = _grade_example(
        tmp_path,
        "python-library.yaml",
        {
            "solution.py": (
                "import math\n\n"
                "def factorial(value):\n"
                "    return math.factorial(value)\n\n"
                "def is_prime(value):\n"
                "    return value > 1 and all(value % n for n in range(2, int(value ** 0.5) + 1))\n"
            )
        },
    )

    assert result.submissions[0].score == 10
    assert result.submissions[0].passed is True


@pytest.mark.integration
def test_sql_example_runs_an_aggregate_query(tmp_path: Path) -> None:
    result = _grade_example(
        tmp_path,
        "sql-query.yaml",
        {
            "query.sql": (
                "SELECT customer, SUM(amount) AS total\n"
                "FROM orders\n"
                "GROUP BY customer\n"
                "ORDER BY customer;\n"
            )
        },
    )

    assert result.submissions[0].score == 10
    assert result.submissions[0].passed is True


@pytest.mark.integration
def test_static_web_example_runs_accessibility_checks(tmp_path: Path) -> None:
    result = _grade_example(
        tmp_path,
        "static-web-page.yaml",
        {
            "index.html": (
                '<!doctype html><html lang="en"><head><title>Profile</title>'
                '<link rel="stylesheet" href="styles.css"></head><body>'
                '<header>Profile</header><main><img src="avatar.png" alt="Ada"></main>'
                "<footer>OpenGrader</footer></body></html>\n"
            ),
            "styles.css": "body { font-family: sans-serif; }\n",
        },
    )

    assert result.submissions[0].score == 10
    assert result.submissions[0].passed is True


@pytest.mark.integration
def test_shell_example_runs_streamed_input_checks(tmp_path: Path) -> None:
    result = _grade_example(
        tmp_path,
        "shell-script.yaml",
        {
            "solution.sh": (
                "#!/bin/sh\n"
                "while IFS= read -r value; do\n"
                "  if [ $((value % 2)) -eq 0 ]; then printf '%s\\n' \"$value\"; fi\n"
                "done\n"
            )
        },
    )

    assert result.submissions[0].score == 10
    assert result.submissions[0].passed is True
