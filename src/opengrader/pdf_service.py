"""Bounded file handling for untrusted PDF submissions."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile

from opengrader.pdf_contract import validate_annotation_page
from opengrader.pdf_grading import (
    PdfGradeRequest,
    PdfSubmissionRecord,
    PdfSubmissionStatus,
    validate_pdf,
    write_feedback_pdf,
)
from opengrader.pdf_repository import PdfSubmissionRepository


class PdfUploadTooLarge(ValueError):
    pass


class PdfGradingService:
    def __init__(
        self,
        repository: PdfSubmissionRepository,
        *,
        storage_root: Path,
        max_upload_bytes: int,
        max_pages: int,
    ) -> None:
        if max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be positive")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        self.repository = repository
        self.storage_root = storage_root
        self.max_upload_bytes = max_upload_bytes
        self.max_pages = max_pages

    async def ingest(
        self,
        upload: UploadFile,
        *,
        student_id: str,
        title: str,
        actor: str,
        assignment_id: str | None = None,
    ) -> PdfSubmissionRecord:
        filename = Path((upload.filename or "").replace("\\", "/")).name
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Upload a file with a .pdf extension")
        if len(filename) > 255 or _has_control_characters(filename):
            raise ValueError("Upload a valid PDF filename")
        student_id = student_id.strip()
        title = title.strip()
        if not student_id:
            raise ValueError("student_id cannot be blank")
        if not title:
            raise ValueError("title cannot be blank")
        if _has_control_characters(student_id) or _has_control_characters(title):
            raise ValueError("PDF metadata cannot contain control characters")

        submission_id = str(uuid.uuid4())
        directory = self.storage_root / submission_id
        directory.mkdir(parents=True, exist_ok=False)
        temporary = directory / "upload.tmp"
        original = directory / "original.pdf"
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("xb") as output:
                while chunk := await upload.read(64 * 1024):
                    size += len(chunk)
                    if size > self.max_upload_bytes:
                        raise PdfUploadTooLarge(
                            f"PDF exceeds the {self.max_upload_bytes} byte upload limit"
                        )
                    digest.update(chunk)
                    output.write(chunk)
            metadata = validate_pdf(temporary, max_pages=self.max_pages)
            temporary.replace(original)
            return self.repository.create_submission(
                submission_id=submission_id,
                student_id=student_id,
                title=title,
                original_filename=filename,
                size_bytes=size,
                sha256=digest.hexdigest(),
                page_count=metadata.page_count,
                actor=actor,
                assignment_id=assignment_id,
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            original.unlink(missing_ok=True)
            directory.rmdir()
            raise
        finally:
            await upload.close()

    def save_grade(
        self, submission_id: str, *, grade: PdfGradeRequest, actor: str
    ) -> PdfSubmissionRecord:
        record = self.repository.get_submission(submission_id)
        if record is None:
            raise KeyError(submission_id)
        for annotation in grade.annotations:
            validate_annotation_page(page=annotation.page, page_count=record.page_count)
        return self.repository.save_grade(submission_id, grade=grade, actor=actor)

    def original_path(self, submission_id: str) -> Path:
        return self.storage_root / submission_id / "original.pdf"

    def feedback_path(self, record: PdfSubmissionRecord) -> Path:
        if record.status is not PdfSubmissionStatus.FINALIZED or record.grade is None:
            raise ValueError("Finalize the grade before exporting feedback")
        destination = self.storage_root / record.id / "feedback.pdf"
        write_feedback_pdf(self.original_path(record.id), destination, record.grade)
        return destination


def _has_control_characters(value: str) -> bool:
    return any(ord(character) < 32 for character in value)
