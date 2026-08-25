"""Extensible LMS provider boundary and adapter registry."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from opengrader.lms import (
    LmsAssignment,
    LmsConnectionStatus,
    LmsCourse,
    LmsProvider,
    StudentIdType,
)


class LmsNotConfigured(RuntimeError):
    pass


class LmsRemoteError(RuntimeError):
    pass


class LmsAdapter(Protocol):
    provider: LmsProvider

    def connection_status(self) -> LmsConnectionStatus: ...
    def list_courses(self) -> list[LmsCourse]: ...
    def list_assignments(self, course_id: str) -> list[LmsAssignment]: ...
    def get_assignment(self, course_id: str, assignment_id: str) -> LmsAssignment: ...
    def post_grade(
        self,
        *,
        course_id: str,
        assignment_id: str,
        student_id: str,
        student_id_type: StudentIdType,
        posted_grade: str,
        comment: str,
    ) -> None: ...


class LmsAdapterRegistry:
    def __init__(self, adapters: Iterable[LmsAdapter] = ()) -> None:
        self._adapters = {adapter.provider: adapter for adapter in adapters}

    def statuses(self) -> list[LmsConnectionStatus]:
        return [
            (
                self._adapters[provider].connection_status()
                if provider in self._adapters
                else LmsConnectionStatus(provider=provider, configured=False)
            )
            for provider in LmsProvider
        ]

    def get(self, provider: LmsProvider) -> LmsAdapter:
        adapter = self._adapters.get(provider)
        if adapter is None or not adapter.connection_status().configured:
            raise LmsNotConfigured(f"{provider.value.title()} is not configured")
        return adapter
