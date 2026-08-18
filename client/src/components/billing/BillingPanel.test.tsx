import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BillingPanel } from "@/components/billing/BillingPanel";
import type { BillingOverview } from "@/types/grader";

function overview(patch: Partial<BillingOverview> = {}): BillingOverview {
  return {
    mode: "hosted",
    status: "none",
    entitled: false,
    customer_configured: false,
    subscription_configured: false,
    current_period_end: null,
    cancel_at_period_end: false,
    usage: { total_units: 0, reported_units: 0, pending_units: 0 },
    ...patch
  };
}

describe("BillingPanel", () => {
  it("makes the free local-edition boundary explicit", () => {
    render(<BillingPanel overview={overview({ mode: "local", entitled: true })} onCheckout={vi.fn()} onPortal={vi.fn()} pending={false} />);

    expect(screen.getByText("Local grading stays free")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Subscribe with Stripe" })).not.toBeInTheDocument();
  });

  it("validates an email and starts hosted Checkout", async () => {
    const user = userEvent.setup();
    const onCheckout = vi.fn();
    render(<BillingPanel overview={overview()} onCheckout={onCheckout} onPortal={vi.fn()} pending={false} />);

    await user.click(screen.getByRole("button", { name: "Subscribe with Stripe" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid billing email");
    await user.type(
      screen.getByRole("textbox", { name: /Billing email/ }),
      "teacher@example.com"
    );
    await user.click(screen.getByRole("button", { name: "Subscribe with Stripe" }));

    expect(onCheckout).toHaveBeenCalledWith("teacher@example.com");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("rejects surrounding text and trims a valid checkout email", () => {
    const onCheckout = vi.fn();
    render(<BillingPanel overview={overview()} onCheckout={onCheckout} onPortal={vi.fn()} pending={false} />);
    const textbox = screen.getByRole("textbox", { name: /Billing email/ });
    const form = textbox.closest("form")!;

    fireEvent.change(textbox, { target: { value: "prefix teacher@example.com" } });
    fireEvent.submit(form);
    fireEvent.change(textbox, { target: { value: "teacher@example.com suffix" } });
    fireEvent.submit(form);
    expect(onCheckout).not.toHaveBeenCalled();

    fireEvent.change(textbox, { target: { value: " teacher@example.com " } });
    fireEvent.submit(form);
    expect(onCheckout).toHaveBeenCalledWith("teacher@example.com");
  });

  it("shows subscription renewal, delivery totals, and billing management", async () => {
    const user = userEvent.setup();
    const onPortal = vi.fn();
    render(
      <BillingPanel
        overview={overview({
          status: "active",
          entitled: true,
          customer_configured: true,
          subscription_configured: true,
          current_period_end: "2026-09-18T00:00:00Z",
          usage: { total_units: 12, reported_units: 10, pending_units: 2 }
        })}
        onCheckout={vi.fn()}
        onPortal={onPortal}
        pending={false}
      />
    );

    expect(screen.getByText("Active subscription")).toBeVisible();
    expect(screen.getByText("12")).toBeVisible();
    expect(screen.getByText("10")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Manage subscription" }));
    expect(onPortal).toHaveBeenCalledOnce();
  });
});
