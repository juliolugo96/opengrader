import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JobStatusBadge } from "@/components/jobs/JobStatusBadge";

describe("JobStatusBadge", () => {
  it.each([
    ["queued", "Queued"],
    ["running", "Running"],
    ["succeeded", "Succeeded"],
    ["failed", "Failed"]
  ] as const)("renders %s status", (status, label) => {
    render(<JobStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeVisible();
  });
});
