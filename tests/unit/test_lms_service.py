from datetime import UTC, datetime
from pathlib import Path

from opengrader.academic import (
    AcademicAssignmentCreate,
    AcademicAssignmentLaunch,
    AcademicContext,
    AssignmentKind,
    AutomatedAssignmentDefinition,
)
from opengrader.academic_repository import AcademicAssignmentRepository
from opengrader.academic_service import AcademicAssignmentService
from opengrader.lms import (
    GradeSyncRequest,
    LmsAssignment,
    LmsAssignmentLinkCreate,
    LmsConnectionStatus,
    LmsCourse,
    LmsProvider,
    StudentIdType,
)
from opengrader.lms_adapter import LmsAdapterRegistry
from opengrader.lms_repository import LmsRepository
from opengrader.lms_service import LmsService
from opengrader.pdf_repository import PdfSubmissionRepository
from opengrader.repository import JobRepository
from opengrader.results import GradingResult, SubmissionResult, TestResult as GraderTestResult


class RecordingCanvasAdapter:
    provider = LmsProvider.CANVAS

    def __init__(self) -> None:
        self.grades: list[dict[str, object]] = []

    def connection_status(self) -> LmsConnectionStatus:
        return LmsConnectionStatus(provider=self.provider, configured=True)

    def list_courses(self) -> list[LmsCourse]:
        return []

    def list_assignments(self, course_id: str) -> list[LmsAssignment]:
        return [self.get_assignment(course_id, "remote-assignment")]

    def get_assignment(self, course_id: str, assignment_id: str) -> LmsAssignment:
        return LmsAssignment(
            id=assignment_id,
            course_id=course_id,
            name="Automated analysis",
            points_possible=20,
        )

    def post_grade(self, **grade: object) -> None:
        self.grades.append(grade)


def test_automated_sync_requires_a_successful_matching_job_and_is_replay_safe(
    tmp_path: Path,
) -> None:
    database = tmp_path / "opengrader.db"
    academic_repository = AcademicAssignmentRepository(database)
    job_repository = JobRepository(database)
    pdf_repository = PdfSubmissionRepository(database)
    lms_repository = LmsRepository(database)
    for repository in (
        academic_repository,
        job_repository,
        pdf_repository,
        lms_repository,
    ):
        repository.initialize()
    academic_service = AcademicAssignmentService(
        academic_repository,
        storage_root=tmp_path / "assignments",
    )
    adapter = RecordingCanvasAdapter()
    service = LmsService(
        registry=LmsAdapterRegistry((adapter,)),
        repository=lms_repository,
        academic_service=academic_service,
        academic_repository=academic_repository,
        job_repository=job_repository,
        pdf_repository=pdf_repository,
    )
    assignment = academic_service.create(
        AcademicAssignmentCreate(
            name="Automated analysis",
            kind=AssignmentKind.AUTOMATED,
            context=AcademicContext(
                institution="Riverdale College",
                course_code="STAT-201",
                course_name="Applied Statistics",
                period="Fall 2026",
                section="B",
            ),
            automated=AutomatedAssignmentDefinition(
                tests=[{"name": "Analysis", "command": "python analysis.py", "points": 20}]
            ),
        ),
        actor="key:professor",
    )
    service.link_assignment(
        LmsProvider.CANVAS,
        LmsAssignmentLinkCreate(
            local_assignment_id=assignment.id,
            external_course_id="course-7",
            external_assignment_id="remote-assignment",
        ),
        actor="key:professor",
    )
    job_request = academic_service.job_request(
        assignment.id,
        AcademicAssignmentLaunch(submissions_dir="submissions"),
    )
    job = job_repository.create_job(job_request, actor="key:professor")
    job_repository.claim_next_job("worker:test")
    job_repository.complete_job(
        job.id,
        result=GradingResult(
            assignment="Automated analysis",
            generated_at=datetime.now(UTC),
            runner="local",
            submissions=[
                SubmissionResult(
                    student_id="S-200",
                    tests=[
                        GraderTestResult(
                            name="Analysis",
                            command="python analysis.py",
                            passed=False,
                            points_earned=15,
                            points_possible=20,
                            exit_code=1,
                            duration_seconds=0.1,
                        )
                    ],
                )
            ],
        ),
        reports={},
        worker_actor="worker:test",
    )

    preview = service.sync_grades(
        assignment.id,
        GradeSyncRequest(job_id=job.id, dry_run=True),
        actor="key:professor",
    )
    sent = service.sync_grades(
        assignment.id,
        GradeSyncRequest(job_id=job.id, student_id_type=StudentIdType.SIS_USER_ID),
        actor="key:professor",
    )
    replay = service.sync_grades(
        assignment.id,
        GradeSyncRequest(job_id=job.id),
        actor="key:professor",
    )

    assert preview.model_dump(include={"attempted", "sent", "skipped", "failed"}) == {
        "attempted": 1,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
    }
    assert preview.deliveries[0].status == "planned"
    assert sent.sent == 1
    assert replay.skipped == 1
    assert adapter.grades == [
        {
            "course_id": "course-7",
            "assignment_id": "remote-assignment",
            "student_id": "S-200",
            "student_id_type": StudentIdType.SIS_USER_ID,
            "posted_grade": "75%",
            "comment": "Grade synchronized from OpenGrader",
        }
    ]
