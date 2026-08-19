import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PdfUploadForm } from "@/components/pdf/PdfUploadForm";
import type { AcademicAssignment } from "@/types/grader";

const assignment: AcademicAssignment = {
  id: "assignment-1", name: "Final essay", kind: "pdf", automated: null,
  context: { institution: "Riverdale College", course_code: "HIST-204", course_name: "Modern History", period: "Fall 2026", section: "B" },
  created_by: "professor", created_at: "2026-08-19T00:00:00Z", updated_at: "2026-08-19T00:00:00Z"
};

describe("PdfUploadForm", () => {
  it("submits PDF bytes with student and assignment metadata", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PdfUploadForm onSubmit={onSubmit} pending={false} />);
    const file = new File(["%PDF-test"], "essay.pdf", { type: "application/pdf" });

    await user.type(screen.getByLabelText("Student ID"), "alice");
    await user.type(screen.getByLabelText("Assignment title"), "Final essay");
    await user.upload(screen.getByLabelText("PDF submission"), file);
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));

    expect(onSubmit).toHaveBeenCalledWith({
      file,
      studentId: "alice",
      title: "Final essay"
    });
  });

  it("associates a submission with a saved written assignment", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const file = new File(["%PDF-test"], "essay.pdf", { type: "application/pdf" });
    render(<PdfUploadForm assignments={[assignment]} initialAssignmentId="assignment-1" onSubmit={onSubmit} pending={false} />);

    await user.type(screen.getByLabelText("Student ID"), "alice");
    await user.upload(screen.getByLabelText("PDF submission"), file);
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));

    expect(onSubmit).toHaveBeenCalledWith({ file, studentId: "alice", title: "Final essay", assignmentId: "assignment-1" });
  });

  it("rejects a non-PDF selection before upload", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const onSubmit = vi.fn();
    render(<PdfUploadForm onSubmit={onSubmit} pending={false} />);

    await user.type(screen.getByLabelText("Student ID"), "alice");
    await user.type(screen.getByLabelText("Assignment title"), "Final essay");
    await user.upload(
      screen.getByLabelText("PDF submission"),
      new File(["plain"], "essay.txt", { type: "text/plain" })
    );
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));

    expect(screen.getByText("Choose a .pdf file.")).toBeVisible();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
