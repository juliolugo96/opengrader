"""Application service for bounded assignment similarity reviews."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pypdf import PdfReader

from opengrader.academic import AssignmentKind
from opengrader.academic_repository import AcademicAssignmentRepository
from opengrader.pdf_grading import PdfSubmissionRecord
from opengrader.pdf_repository import PdfSubmissionRepository
from opengrader.similarity import SimilarityDocument, SimilarityJobRecord, SimilarityJobRequest, SimilarityReport
from opengrader.similarity_contract import analyze_documents
from opengrader.similarity_repository import SimilarityRepository

SimilarityTextExtractor = Callable[[PdfSubmissionRecord, Path], str]


class SimilarityService:
    def __init__(self, repository: SimilarityRepository, academic_repository: AcademicAssignmentRepository, pdf_repository: PdfSubmissionRepository, *, storage_root: Path, text_extractor: SimilarityTextExtractor | None = None) -> None:
        self.repository = repository
        self.academic_repository = academic_repository
        self.pdf_repository = pdf_repository
        self.storage_root = storage_root
        self.text_extractor = text_extractor or extract_pdf_text

    def create(self, request: SimilarityJobRequest, *, actor: str) -> SimilarityJobRecord:
        assignment = self.academic_repository.get(request.assignment_id)
        if assignment is None:
            raise KeyError(request.assignment_id)
        if assignment.kind is not AssignmentKind.PDF:
            raise ValueError("Similarity review currently supports written/PDF assignments")
        submissions: list[PdfSubmissionRecord] = []
        while len(submissions) <= request.policy.max_documents:
            remaining = request.policy.max_documents + 1 - len(submissions)
            page = self.pdf_repository.list_submissions(
                assignment_id=request.assignment_id,
                limit=min(100, remaining),
                offset=len(submissions),
            )
            submissions.extend(page)
            if len(page) < min(100, remaining):
                break
        if len(submissions) > request.policy.max_documents:
            raise ValueError(
                f"Similarity review is limited to {request.policy.max_documents} documents"
            )
        if len(submissions) < 2:
            raise ValueError("At least two PDF submissions are required for similarity review")
        return self.repository.create(request, submission_ids=sorted(record.id for record in submissions), actor=actor)

    def analyze(self, job: SimilarityJobRecord) -> SimilarityReport:
        documents: list[SimilarityDocument] = []
        for submission_id in job.submission_ids:
            record = self.pdf_repository.get_submission(submission_id)
            if record is None or record.assignment_id != job.assignment_id:
                raise ValueError(f"Submission {submission_id} is no longer available in this assignment")
            path = self.storage_root / record.id / "original.pdf"
            text = self.text_extractor(record, path)
            documents.append(SimilarityDocument(submission_id=record.id, student_id=record.student_id, text=text))
        return analyze_documents(assignment_id=job.assignment_id, job_id=job.id, documents=documents, policy=job.request.policy)


def extract_pdf_text(record: PdfSubmissionRecord, path: Path) -> str:
    del record
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
