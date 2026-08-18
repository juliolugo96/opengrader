import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PdfUploadForm } from "@/components/pdf/PdfUploadForm";

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
