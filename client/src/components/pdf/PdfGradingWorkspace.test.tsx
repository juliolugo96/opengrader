import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PdfGradingWorkspace } from "@/components/pdf/PdfGradingWorkspace";
import type { PdfSubmission } from "@/types/grader";

const submission: PdfSubmission = {
  id: "pdf-1",
  assignment_id: null,
  student_id: "alice",
  title: "Final essay",
  original_filename: "essay.pdf",
  size_bytes: 100,
  sha256: "a".repeat(64),
  page_count: 2,
  status: "draft",
  grade: {
    rubric: [{ id: "analysis", title: "Analysis", description: "", max_points: 10 }],
    scores: [{ criterion_id: "analysis", points: 0, feedback: "" }],
    annotations: [],
    overall_feedback: "",
    finalized: false
  },
  total_score: 0,
  maximum_points: 10,
  created_by: "key:test",
  created_at: "2026-08-18T12:00:00Z",
  updated_at: "2026-08-18T12:00:00Z",
  finalized_at: null
};

describe("PdfGradingWorkspace", () => {
  it("saves rubric scores, feedback, and normalized page annotations", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<PdfGradingWorkspace onSave={onSave} pending={false} submission={submission} />);

    await user.clear(screen.getByLabelText("Analysis score"));
    await user.type(screen.getByLabelText("Analysis score"), "8.5");
    await user.type(screen.getByLabelText("Analysis feedback"), "Strong reasoning");
    await user.selectOptions(screen.getByLabelText("Annotation page"), "2");
    await user.clear(screen.getByLabelText("Horizontal position percent"));
    await user.type(screen.getByLabelText("Horizontal position percent"), "25");
    await user.clear(screen.getByLabelText("Vertical position percent"));
    await user.type(screen.getByLabelText("Vertical position percent"), "40");
    await user.type(screen.getByLabelText("Annotation comment"), "Add a citation");
    await user.click(screen.getByRole("button", { name: "Add annotation" }));
    await user.type(screen.getByLabelText("Overall feedback"), "Good work.");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(onSave).toHaveBeenCalledWith({
      rubric: [{ id: "analysis", title: "Analysis", description: "", max_points: 10 }],
      scores: [{ criterion_id: "analysis", points: 8.5, feedback: "Strong reasoning" }],
      annotations: [expect.objectContaining({ page: 2, x: 0.25, y: 0.4, comment: "Add a citation" })],
      overall_feedback: "Good work.",
      finalized: false
    });
  });

  it("locks editing and exposes feedback download after finalization", () => {
    render(
      <PdfGradingWorkspace
        onDownload={vi.fn()}
        onSave={vi.fn()}
        pending={false}
        submission={{ ...submission, status: "finalized", finalized_at: "2026-08-18T13:00:00Z" }}
      />
    );

    expect(screen.getByText("Finalized grade")).toBeVisible();
    expect(screen.getByRole("button", { name: "Download feedback PDF" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save draft" })).not.toBeInTheDocument();
  });

  it("generates a unique criterion ID for a loaded non-sequential rubric", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <PdfGradingWorkspace
        onSave={onSave}
        pending={false}
        submission={{
          ...submission,
          grade: {
            rubric: [{ id: "criterion-2", title: "Evidence", description: "", max_points: 10 }],
            scores: [{ criterion_id: "criterion-2", points: 0, feedback: "" }],
            annotations: [],
            overall_feedback: "",
            finalized: false
          }
        }}
      />
    );

    await user.click(screen.getByRole("button", { name: "Add criterion" }));
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
      rubric: expect.arrayContaining([
        expect.objectContaining({ id: "criterion-2" }),
        expect.objectContaining({ id: "criterion-3" })
      ])
    }));
  });
});
