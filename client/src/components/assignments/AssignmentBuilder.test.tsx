import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AssignmentBuilder } from "@/components/assignments/AssignmentBuilder";

describe("AssignmentBuilder", () => {
  it("creates a PDF assignment using academic language only", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssignmentBuilder onCancel={vi.fn()} onSubmit={onSubmit} pending={false} />);

    await user.click(screen.getByRole("radio", { name: "Written or PDF work" }));
    await user.type(screen.getByLabelText("Institution"), "Riverdale College");
    await user.type(screen.getByLabelText("Course code"), "HIST-204");
    await user.type(screen.getByLabelText("Course name"), "Modern History");
    await user.type(screen.getByLabelText("Academic period"), "Fall 2026");
    await user.type(screen.getByLabelText("Section"), "B");
    await user.type(screen.getByLabelText("Assignment name"), "Primary source essay");
    await user.click(screen.getByRole("button", { name: "Save assignment" }));

    expect(onSubmit).toHaveBeenCalledWith({
      name: "Primary source essay",
      kind: "pdf",
      context: {
        institution: "Riverdale College",
        course_code: "HIST-204",
        course_name: "Modern History",
        period: "Fall 2026",
        section: "B"
      },
      automated: null
    });
    expect(screen.queryByText(/yaml/i)).not.toBeInTheDocument();
  });

  it("turns a programming template and checks into an automated definition", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssignmentBuilder onCancel={vi.fn()} onSubmit={onSubmit} pending={false} />);

    await user.type(screen.getByLabelText("Institution"), "Central High School");
    await user.type(screen.getByLabelText("Course code"), "CS-101");
    await user.type(screen.getByLabelText("Course name"), "Computing Foundations");
    await user.type(screen.getByLabelText("Academic period"), "2026–2027");
    await user.type(screen.getByLabelText("Section"), "1A");
    await user.type(screen.getByLabelText("Assignment name"), "First Python program");
    await user.selectOptions(screen.getByLabelText("Starting point"), "python");
    await user.clear(screen.getByLabelText("Evaluation name 1"));
    await user.type(screen.getByLabelText("Evaluation name 1"), "Greets the reader");
    await user.clear(screen.getByLabelText("Points 1"));
    await user.type(screen.getByLabelText("Points 1"), "25");
    await user.click(screen.getByRole("button", { name: "Save assignment" }));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      name: "First Python program",
      kind: "automated",
      context: expect.objectContaining({ course_code: "CS-101", section: "1A" }),
      automated: expect.objectContaining({
        image: "python:3.12-slim",
        tests: [expect.objectContaining({ name: "Greets the reader", points: 25 })]
      })
    }));
  });
});
