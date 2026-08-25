"""Pure identifier and score rules shared by LMS adapters and services."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum


class StudentIdType(StrEnum):
    CANVAS_USER_ID = "canvas_user_id"
    SIS_USER_ID = "sis_user_id"
    LOGIN_ID = "login_id"


def canvas_user_reference(student_id: str, identifier_type: StudentIdType) -> str:
    normalized = student_id.strip()
    if not normalized or any(character in normalized for character in "/?#"):
        raise ValueError("student identifiers must be nonblank path-safe values")
    if identifier_type is StudentIdType.SIS_USER_ID:
        return f"sis_user_id:{normalized}"
    if identifier_type is StudentIdType.LOGIN_ID:
        return f"sis_login_id:{normalized}"
    return normalized


def grade_percentage(score: float, maximum: float) -> str:
    if maximum <= 0:
        raise ValueError("maximum score must be positive")
    if score < 0 or score > maximum:
        raise ValueError("score must be between zero and the maximum")
    percentage = (
        Decimal(str(score)) / Decimal(str(maximum)) * Decimal("100")
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    rendered = format(percentage, "f").rstrip("0").rstrip(".")
    return f"{rendered}%"
