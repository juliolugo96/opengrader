import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { NewJobModal } from "@/components/jobs/NewJobModal";

describe("NewJobModal", () => {
  it("blocks invalid paths and submits a valid job", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<NewJobModal onClose={vi.fn()} onSubmit={onSubmit} open pending={false} />);

    const assignment = screen.getByLabelText("Assignment YAML path");
    await user.clear(assignment);
    await user.click(screen.getByRole("button", { name: "Start grading" }));
    expect(screen.getByText("Enter an assignment YAML path.")).toBeVisible();
    expect(onSubmit).not.toHaveBeenCalled();

    await user.type(assignment, "assignments/final.yaml");
    await user.click(screen.getByRole("button", { name: "Start grading" }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ assignmentPath: "assignments/final.yaml" }));
  });
});
