from pathlib import Path

import pytest

from opengrader.errors import SubmissionError
from opengrader.submissions import Submission, select_submissions

pytestmark = pytest.mark.unit


def submission(name: str) -> Submission:
    return Submission(name, Path("/submissions") / name)


def test_selects_union_of_patterns_without_duplicates_in_original_order() -> None:
    submissions = [submission("alice"), submission("bob"), submission("carol")]

    selected = select_submissions(submissions, ["b*", "alice", "*"])

    assert [item.student_id for item in selected] == ["alice", "bob", "carol"]


def test_no_patterns_selects_everything() -> None:
    submissions = [submission("alice"), submission("bob")]

    assert select_submissions(submissions, []) == submissions


def test_unmatched_pattern_is_rejected() -> None:
    with pytest.raises(SubmissionError, match="nobody\\*.*matched no submissions"):
        select_submissions([submission("alice")], ["nobody*"])
