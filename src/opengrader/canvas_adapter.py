"""Canvas REST adapter with bounded same-origin pagination."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from opengrader.lms import (
    LmsAssignment,
    LmsConnectionStatus,
    LmsCourse,
    LmsProvider,
    StudentIdType,
    canvas_user_reference,
)
from opengrader.lms_adapter import LmsRemoteError


@dataclass(frozen=True, slots=True)
class CanvasResponse:
    payload: object
    headers: dict[str, str]


class CanvasTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
    ) -> CanvasResponse: ...


class UrlLibCanvasTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
    ) -> CanvasResponse:
        request = urllib.request.Request(
            url, data=body, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
                response_headers = {
                    key.lower(): value for key, value in response.headers.items()
                }
        except urllib.error.HTTPError as exc:
            message = exc.read(2_000).decode("utf-8", errors="replace")
            raise LmsRemoteError(
                f"Canvas returned HTTP {exc.code}: {message or exc.reason}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LmsRemoteError("Canvas could not be reached or returned invalid JSON") from exc
        return CanvasResponse(payload=payload, headers=response_headers)


class CanvasAdapter:
    provider = LmsProvider.CANVAS

    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        account_name: str | None = None,
        transport: CanvasTransport | None = None,
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url.strip())
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("Canvas base URL must be a credential-free HTTPS origin")
        token = access_token.strip()
        if not token:
            raise ValueError("Canvas access token must not be blank")
        self.base_url = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, "", "", "")
        )
        self._origin = (parsed.scheme, parsed.hostname, parsed.port)
        self._access_token = token
        self._account_name = account_name.strip() if account_name else None
        self._transport = transport or UrlLibCanvasTransport()

    def connection_status(self) -> LmsConnectionStatus:
        return LmsConnectionStatus(
            provider=self.provider,
            configured=True,
            account_name=self._account_name,
            base_url=self.base_url,
        )

    def list_courses(self) -> list[LmsCourse]:
        query = urllib.parse.urlencode(
            [
                ("enrollment_type", "teacher"),
                ("state[]", "available"),
                ("include[]", "term"),
                ("per_page", "100"),
            ]
        )
        payloads = self._get_pages(f"{self.base_url}/api/v1/courses?{query}")
        courses: list[LmsCourse] = []
        for item in payloads:
            if not isinstance(item, dict):
                raise LmsRemoteError("Canvas returned an invalid course")
            term = item.get("term")
            courses.append(
                LmsCourse(
                    id=_required_text(item, "id"),
                    name=_required_text(item, "name", limit=300),
                    course_code=_optional_text(item.get("course_code"), limit=100),
                    term=(
                        _optional_text(term.get("name"), limit=160)
                        if isinstance(term, dict)
                        else None
                    ),
                )
            )
        return courses

    def list_assignments(self, course_id: str) -> list[LmsAssignment]:
        course = _path_id(course_id)
        query = urllib.parse.urlencode(
            [("order_by", "name"), ("per_page", "100")]
        )
        payloads = self._get_pages(
            f"{self.base_url}/api/v1/courses/{course}/assignments?{query}"
        )
        return [self._assignment(item, course_id) for item in payloads]

    def get_assignment(self, course_id: str, assignment_id: str) -> LmsAssignment:
        course = _path_id(course_id)
        assignment = _path_id(assignment_id)
        response = self._request(
            "GET",
            f"{self.base_url}/api/v1/courses/{course}/assignments/{assignment}",
        )
        return self._assignment(response.payload, course_id)

    def post_grade(
        self,
        *,
        course_id: str,
        assignment_id: str,
        student_id: str,
        student_id_type: StudentIdType,
        posted_grade: str,
        comment: str,
    ) -> None:
        user_reference = canvas_user_reference(student_id, student_id_type)
        body = urllib.parse.urlencode(
            {
                "submission[posted_grade]": posted_grade,
                "comment[text_comment]": comment,
            }
        ).encode("utf-8")
        self._request(
            "PUT",
            f"{self.base_url}/api/v1/courses/{_path_id(course_id)}"
            f"/assignments/{_path_id(assignment_id)}/submissions/{_path_id(user_reference)}",
            body=body,
        )

    def _get_pages(self, initial_url: str) -> list[object]:
        url: str | None = initial_url
        items: list[object] = []
        pages = 0
        while url is not None:
            pages += 1
            if pages > 50:
                raise LmsRemoteError("Canvas pagination exceeded 50 pages")
            self._require_same_origin(url)
            response = self._request("GET", url)
            if not isinstance(response.payload, list):
                raise LmsRemoteError("Canvas returned a non-list collection")
            items.extend(response.payload)
            url = _next_link(response.headers.get("link"))
        return items

    def _request(self, method: str, url: str, *, body: bytes | None = None) -> CanvasResponse:
        self._require_same_origin(url)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": "OpenGrader/0.7",
        }
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return self._transport.request(method, url, headers=headers, body=body)

    def _require_same_origin(self, url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme, parsed.hostname, parsed.port) != self._origin:
            raise LmsRemoteError("Canvas pagination attempted to leave its configured origin")

    @staticmethod
    def _assignment(payload: object, course_id: str) -> LmsAssignment:
        if not isinstance(payload, dict):
            raise LmsRemoteError("Canvas returned an invalid assignment")
        submission_types = payload.get("submission_types", [])
        if not isinstance(submission_types, list):
            submission_types = []
        return LmsAssignment(
            id=_required_text(payload, "id"),
            course_id=str(payload.get("course_id", course_id)),
            name=_required_text(payload, "name", limit=300),
            description=_optional_text(payload.get("description"), limit=20_000),
            points_possible=payload.get("points_possible"),
            due_at=payload.get("due_at"),
            published=bool(payload.get("published", False)),
            submission_types=[str(value)[:100] for value in submission_types[:50]],
        )


def _path_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Canvas identifier must not be blank")
    return urllib.parse.quote(normalized, safe="")


def _required_text(payload: dict[str, object], key: str, *, limit: int = 200) -> str:
    value = _optional_text(payload.get(key), limit=limit)
    if not value:
        raise LmsRemoteError(f"Canvas {key} is missing")
    return value


def _optional_text(value: object, *, limit: int) -> str:
    return "" if value is None else str(value).strip()[:limit]


def _next_link(header: str | None) -> str | None:
    if not header:
        return None
    for part in header.split(","):
        if re.search(r'rel\s*=\s*"?next"?', part, flags=re.IGNORECASE):
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None
