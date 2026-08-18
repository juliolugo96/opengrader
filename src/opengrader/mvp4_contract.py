"""Pure compatibility and aggregation rules introduced by the MVP 4 dashboard."""

from __future__ import annotations

from typing import Any

from opengrader.results import GradingResult


def normalize_job_request_payload(value: Any) -> Any:
    """Accept the MVP 4 public field names while preserving MVP 3 storage names."""
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    if "assignment_path" in normalized:
        if "assignment_file" in normalized:
            raise ValueError("use either assignment_path or assignment_file, not both")
        normalized["assignment_file"] = normalized.pop("assignment_path")
    if "submission_filter" in normalized:
        if "submission_patterns" in normalized:
            raise ValueError(
                "use either submission_filter or submission_patterns, not both"
            )
        submission_filter = normalized.pop("submission_filter")
        normalized["submission_patterns"] = (
            [submission_filter] if submission_filter else []
        )
    return normalized


def cohort_totals(result: GradingResult) -> tuple[float, float, int]:
    """Return stable cohort totals without leaking binary floating-point noise."""
    return (
        round(sum(item.score for item in result.submissions), 6),
        round(sum(item.maximum_score for item in result.submissions), 6),
        len(result.submissions),
    )


def validate_job_page(*, limit: int, offset: int) -> None:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("offset must be non-negative")
