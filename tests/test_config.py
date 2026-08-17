from pathlib import Path

import pytest

from opengrader.config import AssignmentConfig, load_assignment
from opengrader.errors import ConfigError


def test_load_assignment_applies_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "assignment.yaml"
    config_file.write_text(
        "name: Example\ntests:\n  - name: Smoke\n    command: python app.py\n",
        encoding="utf-8",
    )

    assignment = load_assignment(config_file)

    assert assignment.name == "Example"
    assert assignment.image == "python:3.12-slim"
    assert assignment.tests[0].points == 1
    assert assignment.maximum_score == 1


@pytest.mark.parametrize(
    "yaml_text, expected",
    [
        ("name: Empty\ntests: []\n", "tests"),
        (
            "name: Duplicate\ntests:\n"
            "  - {name: Same, command: 'true'}\n"
            "  - {name: Same, command: 'true'}\n",
            "unique",
        ),
        ("name: Typo\ntimeout: 2\ntests: [{name: A, command: 'true'}]\n", "timeout"),
    ],
)
def test_invalid_assignment_has_useful_error(
    tmp_path: Path, yaml_text: str, expected: str
) -> None:
    config_file = tmp_path / "assignment.yaml"
    config_file.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(ConfigError, match=expected):
        load_assignment(config_file)


def test_model_rejects_non_positive_points() -> None:
    with pytest.raises(ValueError):
        AssignmentConfig.model_validate(
            {"name": "Example", "tests": [{"name": "A", "command": "true", "points": 0}]}
        )

