import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlanCatalog } from "@/components/plans/PlanCatalog";

describe("PlanCatalog", () => {
  it("presents Community, Hosted, and Institution scope truthfully", () => {
    render(<PlanCatalog />);

    expect(screen.getByRole("heading", { name: "Community" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Hosted" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Institution" })).toBeVisible();
    expect(screen.getByText("Free")).toBeVisible();
    expect(screen.getByText("Usage based")).toBeVisible();
    expect(screen.getByText("Custom")).toBeVisible();
    expect(screen.getByText("Early access")).toBeVisible();
  });

  it("labels roadmap capabilities as planned and implemented capabilities without that label", () => {
    render(<PlanCatalog />);
    const institution = screen.getByRole("heading", { name: "Institution" }).closest("article")!;
    const community = screen.getByRole("heading", { name: "Community" }).closest("article")!;

    expect(within(institution).getByText("Role-based access").closest("li")).toHaveTextContent("Planned");
    expect(within(institution).getByText("Canvas grade synchronization").closest("li")).toHaveTextContent("Available now");
    expect(within(community).getByText("Local CLI and grading engine").closest("li")).not.toHaveTextContent("Planned");
  });
});
