from pathlib import Path

from opengrader.lms import LmsProvider
from opengrader.lms_repository import LmsRepository


def test_links_and_grade_delivery_are_durable_and_idempotent(tmp_path: Path) -> None:
    repository = LmsRepository(tmp_path / "jobs.db")
    repository.initialize()

    link = repository.create_link(
        local_assignment_id="local-1",
        provider=LmsProvider.CANVAS,
        external_course_id="course-7",
        external_assignment_id="assignment-9",
        actor="key:professor",
    )
    assert repository.get_link("local-1") == link
    assert repository.list_links() == [link]

    assert repository.was_delivered("delivery-key") is False
    repository.record_delivery(
        delivery_key="delivery-key",
        link_id=link.id,
        student_id="S-100",
        posted_grade="85%",
        source_revision="job-1",
        actor="key:professor",
    )
    assert repository.was_delivered("delivery-key") is True
    repository.record_delivery(
        delivery_key="delivery-key",
        link_id=link.id,
        student_id="S-100",
        posted_grade="85%",
        source_revision="job-1",
        actor="key:professor",
    )
    assert repository.delivery_count() == 1


def test_one_local_assignment_cannot_be_linked_twice(tmp_path: Path) -> None:
    repository = LmsRepository(tmp_path / "jobs.db")
    repository.initialize()
    repository.create_link(
        local_assignment_id="local-1", provider=LmsProvider.CANVAS,
        external_course_id="7", external_assignment_id="9", actor="key:professor",
    )

    try:
        repository.create_link(
            local_assignment_id="local-1", provider=LmsProvider.CANVAS,
            external_course_id="7", external_assignment_id="10", actor="key:professor",
        )
    except ValueError as exc:
        assert "already linked" in str(exc)
    else:
        raise AssertionError("duplicate local assignment link was accepted")
