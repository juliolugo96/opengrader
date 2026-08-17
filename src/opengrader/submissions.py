"""Folder-based submission discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from opengrader.errors import SubmissionError


@dataclass(frozen=True, slots=True)
class Submission:
    """A submission discovered as a direct child directory."""

    student_id: str
    path: Path


def discover_submissions(root: Path) -> list[Submission]:
    """Return visible direct child directories in deterministic order."""

    if not root.exists():
        raise SubmissionError(f"Submissions directory does not exist: '{root}'")
    if not root.is_dir():
        raise SubmissionError(f"Submissions path is not a directory: '{root}'")

    submissions = [
        Submission(student_id=path.name, path=path.resolve())
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]
    submissions.sort(key=lambda submission: submission.student_id.casefold())

    if not submissions:
        raise SubmissionError(f"No submission folders found in '{root}'")
    return submissions

