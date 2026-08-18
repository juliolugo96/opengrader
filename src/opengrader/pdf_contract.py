"""Pure invariants shared by PDF grading models, services, and exports."""

from __future__ import annotations

from typing import Protocol, Sequence


class CriterionLike(Protocol):
    id: str
    max_points: float


class ScoreLike(Protocol):
    criterion_id: str
    points: float


def validate_rubric_scores(
    rubric: Sequence[CriterionLike], scores: Sequence[ScoreLike]
) -> None:
    criteria_by_id = {criterion.id: criterion for criterion in rubric}
    if len(criteria_by_id) != len(rubric):
        raise ValueError("criterion IDs must be unique")

    scores_by_id = {score.criterion_id: score for score in scores}
    if len(scores_by_id) != len(scores):
        raise ValueError("score criterion IDs must be unique")
    if set(scores_by_id) != set(criteria_by_id):
        raise ValueError("scores must match rubric criteria exactly")

    for criterion_id, score in scores_by_id.items():
        maximum = criteria_by_id[criterion_id].max_points
        if score.points > maximum:
            raise ValueError(f"score for '{criterion_id}' cannot exceed {maximum:g}")


def rubric_totals(
    rubric: Sequence[CriterionLike], scores: Sequence[ScoreLike]
) -> tuple[float, float]:
    return (
        round(sum(score.points for score in scores), 6),
        round(sum(criterion.max_points for criterion in rubric), 6),
    )


def validate_annotation_page(*, page: int, page_count: int) -> None:
    if page > page_count:
        raise ValueError(
            f"Annotation page {page} exceeds document page count {page_count}"
        )


def annotation_rect(
    *, x: float, y: float, width: float, height: float, marker_size: float = 18
) -> tuple[float, float, float, float]:
    left = min(x * width, max(width - marker_size, 0))
    bottom = min((1 - y) * height, max(height - marker_size, 0))
    return (left, bottom, left + marker_size, bottom + marker_size)
