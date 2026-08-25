import pytest

from opengrader.canvas_adapter import CanvasAdapter, CanvasResponse
from opengrader.lms import StudentIdType
from opengrader.lms_adapter import LmsRemoteError


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, bytes | None]] = []
        self.responses: list[CanvasResponse] = []

    def request(self, method: str, url: str, *, headers, body=None) -> CanvasResponse:
        assert headers["Authorization"] == "Bearer secret-token"
        self.requests.append((method, url, body))
        return self.responses.pop(0)


def test_canvas_adapter_paginates_courses_and_normalizes_assignments() -> None:
    transport = FakeTransport()
    transport.responses = [
        CanvasResponse(
            payload=[{"id": 7, "name": "Biology", "course_code": "BIO-101"}],
            headers={"link": '<https://canvas.example/api/v1/courses?page=2>; rel="next"'},
        ),
        CanvasResponse(
            payload=[{"id": 8, "name": "Chemistry", "course_code": "CHEM-101"}],
            headers={},
        ),
        CanvasResponse(
            payload=[{
                "id": 99,
                "course_id": 7,
                "name": "Lab report",
                "description": "<p>Upload the report</p>",
                "points_possible": 20,
                "due_at": "2026-09-20T23:59:00Z",
                "published": True,
                "submission_types": ["online_upload"],
            }],
            headers={},
        ),
    ]
    adapter = CanvasAdapter(
        base_url="https://canvas.example/", access_token="secret-token", transport=transport
    )

    courses = adapter.list_courses()
    assignments = adapter.list_assignments("7")

    assert [course.id for course in courses] == ["7", "8"]
    assert assignments[0].name == "Lab report"
    assert assignments[0].points_possible == 20
    assert transport.requests[0][1].startswith("https://canvas.example/api/v1/courses?")
    assert transport.requests[1][1].endswith("page=2")
    assert "/courses/7/assignments?" in transport.requests[2][1]


def test_canvas_adapter_posts_percent_grade_with_encoded_sis_reference() -> None:
    transport = FakeTransport()
    transport.responses = [CanvasResponse(payload={"id": 1}, headers={})]
    adapter = CanvasAdapter(
        base_url="https://canvas.example", access_token="secret-token", transport=transport
    )

    adapter.post_grade(
        course_id="course 7",
        assignment_id="assignment/9",
        student_id="S 100",
        student_id_type=StudentIdType.SIS_USER_ID,
        posted_grade="87.5%",
        comment="Synced from OpenGrader",
    )

    method, url, body = transport.requests[0]
    assert method == "PUT"
    assert "/courses/course%207/assignments/assignment%2F9/submissions/sis_user_id%3AS%20100" in url
    assert body == b"submission%5Bposted_grade%5D=87.5%25&comment%5Btext_comment%5D=Synced+from+OpenGrader"


def test_canvas_adapter_rejects_insecure_or_credentialed_origins() -> None:
    for base_url in ("http://canvas.example", "https://user:pass@canvas.example", "file:///tmp/canvas"):
        try:
            CanvasAdapter(base_url=base_url, access_token="secret-token")
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted unsafe Canvas URL: {base_url}")


def test_canvas_adapter_refuses_cross_origin_pagination() -> None:
    transport = FakeTransport()
    transport.responses = [CanvasResponse(
        payload=[],
        headers={"link": '<https://attacker.example/steal>; rel="next"'},
    )]
    adapter = CanvasAdapter(
        base_url="https://canvas.example", access_token="secret-token", transport=transport
    )

    with pytest.raises(LmsRemoteError, match="leave its configured origin"):
        adapter.list_courses()
    assert len(transport.requests) == 1
