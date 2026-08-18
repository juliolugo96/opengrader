import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JobStatusBadge } from "@/components/jobs/JobStatusBadge";

describe("JobStatusBadge", () => {
  it.each(["queued", "running", "succeeded", "failed"] as const)("renders %s status", (status) => {
    render(<JobStatusBadge status={status} />);
    expect(screen.getByText(status)).toBeVisible();
  });
});
