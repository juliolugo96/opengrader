import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LmsWorkspace } from "@/components/lms/LmsWorkspace";
import type { AcademicAssignment, LmsAssignmentLink, LmsCourse, LmsRemoteAssignment } from "@/types/grader";

const courses: LmsCourse[] = [{ id: "7", name: "World History", course_code: "HIST-204", term: "Fall 2026" }];
const remoteAssignments: LmsRemoteAssignment[] = [{
  id: "99", course_id: "7", name: "Primary source essay", description: "Essay",
  points_possible: 40, due_at: null, published: true, submission_types: ["online_upload"]
}];
const localAssignment: AcademicAssignment = {
  id: "local-1", name: "Primary source essay", kind: "pdf",
  context: { institution: "Riverdale College", course_code: "HIST-204", course_name: "World History", period: "Fall 2026", section: "A" },
  automated: null, created_by: "key:test", created_at: "2026-08-21T00:00:00Z", updated_at: "2026-08-21T00:00:00Z"
};
const links: LmsAssignmentLink[] = [{
  id: "link-1", local_assignment_id: "local-1", provider: "canvas",
  external_course_id: "7", external_assignment_id: "99",
  created_by: "key:test", created_at: "2026-08-21T00:00:00Z", updated_at: "2026-08-21T00:00:00Z"
}];

describe("LmsWorkspace", () => {
  it("explains server-owned Canvas configuration without exposing a token field", () => {
    render(
      <LmsWorkspace
        assignments={[]} courses={[]} links={[]} localAssignments={[]}
        onImport={vi.fn()} onLink={vi.fn()} onSelectCourse={vi.fn()} onSync={vi.fn()}
        pending={false}
        status={{ provider: "canvas", configured: false, account_name: null, base_url: null }}
      />
    );

    expect(screen.getByText("Canvas is not configured")).toBeVisible();
    expect(screen.getByText(/server environment/i)).toBeVisible();
    expect(screen.queryByLabelText(/access token/i)).not.toBeInTheDocument();
  });

  it("browses a course and imports a remote assignment with academic context", async () => {
    const user = userEvent.setup();
    const onSelectCourse = vi.fn();
    const onImport = vi.fn();
    render(
      <LmsWorkspace
        assignments={remoteAssignments} courses={courses} links={[]}
        localAssignments={[]} onImport={onImport} onLink={vi.fn()}
        onSelectCourse={onSelectCourse} onSync={vi.fn()} pending={false}
        status={{ provider: "canvas", configured: true, account_name: "Riverdale Canvas", base_url: "https://canvas.example" }}
      />
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Canvas course" }), "7");
    expect(onSelectCourse).toHaveBeenCalledWith("7");
    await user.click(screen.getByRole("button", { name: "Import Primary source essay" }));
    await user.type(screen.getByRole("textbox", { name: "Institution" }), "Riverdale College");
    await user.type(screen.getByRole("textbox", { name: "Course code" }), "HIST-204");
    await user.type(screen.getByRole("textbox", { name: "Course name" }), "World History");
    await user.type(screen.getByRole("textbox", { name: "Academic period" }), "Fall 2026");
    await user.type(screen.getByRole("textbox", { name: "Section" }), "A");
    await user.click(screen.getByRole("button", { name: "Import assignment" }));

    expect(onImport).toHaveBeenCalledWith(expect.objectContaining({
      external_course_id: "7", external_assignment_id: "99", kind: "pdf",
      context: expect.objectContaining({ institution: "Riverdale College", section: "A" })
    }));
  });

  it("supports a dry run before sending linked grades", async () => {
    const user = userEvent.setup();
    const onSync = vi.fn();
    render(
      <LmsWorkspace
        assignments={[]} courses={courses} links={links}
        localAssignments={[localAssignment]} onImport={vi.fn()} onLink={vi.fn()}
        onSelectCourse={vi.fn()} onSync={onSync} pending={false}
        status={{ provider: "canvas", configured: true, account_name: "Riverdale Canvas", base_url: "https://canvas.example" }}
      />
    );

    await user.click(screen.getByRole("checkbox", { name: "Dry run" }));
    await user.click(screen.getByRole("button", { name: "Synchronize Primary source essay" }));
    expect(onSync).toHaveBeenCalledWith("local-1", {
      dry_run: true, job_id: null, student_id_type: "sis_user_id"
    });
  });
});
