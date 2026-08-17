"""Assignment YAML loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from opengrader.errors import ConfigError


class TestConfig(BaseModel):
    """One pass/fail command in an assignment rubric."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    points: float = Field(default=1.0, gt=0)
    timeout_seconds: float | None = Field(default=None, gt=0, le=3600)

    @field_validator("name", "command")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class AssignmentConfig(BaseModel):
    """Validated assignment definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    image: str = Field(default="python:3.12-slim", min_length=1)
    setup: str | None = None
    timeout_seconds: float = Field(default=10.0, gt=0, le=3600)
    memory_mb: int = Field(default=256, ge=32, le=32768)
    cpus: float = Field(default=1.0, gt=0, le=32)
    pids_limit: int = Field(default=128, ge=16, le=4096)
    tests: list[TestConfig] = Field(min_length=1)

    @field_validator("name", "image")
    @classmethod
    def assignment_text_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("setup")
    @classmethod
    def setup_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("tests")
    @classmethod
    def test_names_are_unique(cls, tests: list[TestConfig]) -> list[TestConfig]:
        names = [test.name for test in tests]
        if len(names) != len(set(names)):
            raise ValueError("test names must be unique")
        return tests

    @property
    def maximum_score(self) -> float:
        return sum(test.points for test in self.tests)


def load_assignment(path: Path) -> AssignmentConfig:
    """Load an assignment from YAML and return a validated model."""

    try:
        with path.open(encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)
    except OSError as exc:
        raise ConfigError(f"Could not read assignment file '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in '{path}': {exc}") from exc

    if raw is None:
        raise ConfigError(f"Assignment file '{path}' is empty")
    if not isinstance(raw, dict):
        raise ConfigError("Assignment YAML must contain a top-level mapping")

    try:
        return AssignmentConfig.model_validate(raw)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigError(f"Invalid assignment configuration: {details}") from exc

