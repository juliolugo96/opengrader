import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SimilarityWorkspace } from "@/components/similarity/SimilarityWorkspace";
import type { AcademicAssignment, SimilarityReport } from "@/types/grader";

const assignment: AcademicAssignment = {
  id: "essay-1", name: "Coastal systems", kind: "pdf", automated: null,
  context: { institution: "Northstar", course_code: "BIO-201", course_name: "Ecology", period: "Spring 2027", section: "A" },
  created_by: "key:test", created_at: "2027-01-01T00:00:00Z", updated_at: "2027-01-01T00:00:00Z"
};

const report: SimilarityReport = {
  job_id: "job-1", assignment_id: "essay-1", algorithm_version: "structural-winnowing-v1",
  generated_at: "2027-01-01T00:01:00Z", corpus_size: 2, candidate_pairs_evaluated: 1,
  indeterminate_documents: [], warnings: [],
  disclaimer: "Similarity signals support instructor review; they do not determine plagiarism or academic misconduct.",
  matches: [{
    left_submission_id: "left", left_student_id: "alice", right_submission_id: "right", right_student_id: "bob",
    score: 0.72, containment: 0.8, jaccard: 0.6, coverage: 0.6, band: "high_signal", exact_match: false,
    shared_fingerprints: 8,
    evidence: [{ fingerprint: "abc", left_excerpt: "the coastal habitat declines", right_excerpt: "the coastal habitat declines", left_start: 0, left_end: 10, right_start: 4, right_end: 14 }]
  }]
};

describe("SimilarityWorkspace", () => {
  it("requires two submissions before starting an assignment-scoped review", () => {
    render(<SimilarityWorkspace assignmentId="essay-1" assignments={[assignment]} jobs={[]} onAssignmentChange={vi.fn()} onStart={vi.fn()} pending={false} submissionCounts={{ "essay-1": 1 }} />);
    expect(screen.getByRole("button", { name: "Start review" })).toBeDisabled();
    expect(screen.getByText(/at least two submissions/i)).toBeVisible();
  });

  it("starts a review and explains evidence without a verdict", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<SimilarityWorkspace assignmentId="essay-1" assignments={[assignment]} jobs={[]} onAssignmentChange={vi.fn()} onStart={onStart} pending={false} report={report} submissionCounts={{ "essay-1": 2 }} />);
    await user.click(screen.getByRole("button", { name: "Start review" }));
    expect(onStart).toHaveBeenCalledOnce();
    expect(screen.getByText("alice ↔ bob")).toBeVisible();
    expect(screen.getAllByText("the coastal habitat declines")).toHaveLength(2);
    expect(screen.getByText(/do not determine plagiarism/i)).toBeVisible();
    expect(screen.queryByText(/guilty/i)).not.toBeInTheDocument();
  });
});
