from types import SimpleNamespace

import pytest

from opengrader.pdf_contract import (
    annotation_rect,
    rubric_totals,
    validate_annotation_page,
    validate_rubric_scores,
)

pytestmark = pytest.mark.unit


def criterion(identifier: str, maximum: float):
    return SimpleNamespace(id=identifier, max_points=maximum)


def score(identifier: str, points: float):
    return SimpleNamespace(criterion_id=identifier, points=points)


def test_rubric_contract_accepts_exact_bounded_score_mapping() -> None:
    assert validate_rubric_scores(
        [criterion("analysis", 6), criterion("evidence", 4)],
        [score("analysis", 6), score("evidence", 4)],
    ) is None


@pytest.mark.parametrize(
    ("rubric", "scores", "message"),
    [
        (
            [criterion("same", 2), criterion("same", 3)],
            [score("same", 1)],
            "criterion IDs must be unique",
        ),
        (
            [criterion("a", 2)],
            [score("a", 1), score("a", 1)],
            "score criterion IDs must be unique",
        ),
        (
            [criterion("a", 2)],
            [score("b", 1)],
            "scores must match rubric criteria exactly",
        ),
        (
            [criterion("a", 2)],
            [score("a", 2.1)],
            "score for 'a' cannot exceed 2",
        ),
    ],
)
def test_rubric_contract_rejects_ambiguous_or_unbounded_scores(
    rubric, scores, message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        validate_rubric_scores(rubric, scores)


def test_rubric_totals_round_to_six_decimal_places() -> None:
    assert rubric_totals(
        [criterion("a", 0.7654321)], [score("a", 0.1234567)]
    ) == (0.123457, 0.765432)


def test_annotation_page_includes_last_page_and_rejects_the_next() -> None:
    assert validate_annotation_page(page=2, page_count=2) is None
    with pytest.raises(
        ValueError, match="^Annotation page 3 exceeds document page count 2$"
    ):
        validate_annotation_page(page=3, page_count=2)


def test_annotation_rectangle_maps_top_left_coordinates_and_clamps_marker() -> None:
    assert annotation_rect(x=0.25, y=0.4, width=612, height=792) == pytest.approx(
        (153, 475.2, 171, 493.2)
    )
    assert annotation_rect(x=1, y=0, width=612, height=792) == (
        594,
        774,
        612,
        792,
    )
    assert annotation_rect(x=1, y=0, width=10, height=10) == (0, 0, 18, 18)
