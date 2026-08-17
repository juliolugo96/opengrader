from pathlib import Path

import pytest

from opengrader.errors import SubmissionError
from opengrader.submissions import discover_submissions


def test_discovers_visible_directories_in_stable_order(tmp_path: Path) -> None:
    (tmp_path / "zoe").mkdir()
    (tmp_path / "Alice").mkdir()
    (tmp_path / ".cache").mkdir()
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    submissions = discover_submissions(tmp_path)

    assert [submission.student_id for submission in submissions] == ["Alice", "zoe"]
    assert all(submission.path.is_absolute() for submission in submissions)


def test_empty_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SubmissionError, match="No submission folders"):
        discover_submissions(tmp_path)

