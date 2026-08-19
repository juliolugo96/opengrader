import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

import type { AcademicAssignment, BillingOverview, PdfGradeRequest, PdfSubmission } from "../../src/types/grader";

const { Given, When, Then } = createBdd();

const completedJob = {
  id: "job-succeeded",
  status: "succeeded",
  request: {
    assignment_file: "assignments/hw1.yaml",
    submissions_dir: "submissions",
    no_docker: false,
    workers: 4,
    retries: 1,
    submission_patterns: []
  },
  created_by: "key:0123456789ab",
  created_at: "2026-08-17T12:00:00Z",
  updated_at: "2026-08-17T12:00:05Z",
  started_at: "2026-08-17T12:00:01Z",
  completed_at: "2026-08-17T12:00:05Z",
  reports: { json: "results.json", csv: "results.csv" },
  error: null
};

const jobs = [
  completedJob,
  ...Array.from({ length: 10 }, (_, index) => ({
    ...completedJob,
    id: `job-${String(index + 2).padStart(3, "0")}`,
    status: index === 0 ? "running" : index === 1 ? "failed" : "succeeded",
    request: { ...completedJob.request, assignment_file: `assignments/hw${index + 2}.yaml` },
    created_at: `2026-08-16T${String(22 - index).padStart(2, "0")}:00:00Z`,
    error: index === 1 ? "grader failed" : null
  }))
];

const resultResponse = {
  job_id: completedJob.id,
  reports: completedJob.reports,
  statistics: { total_score: 8, maximum_points: 10, student_count: 1 },
  result: {
    assignment: "Homework 1",
    generated_at: "2026-08-17T12:00:05Z",
    runner: "docker",
    workers: 4,
    retries: 1,
    submissions: [{
      student_id: "alice",
      score: 8,
      maximum_score: 10,
      passed: true,
      status: "pass",
      tests: [{
        name: "passes tests",
        command: "pytest -q",
        passed: true,
        status: "pass",
        points_earned: 8,
        points_possible: 10,
        exit_code: 0,
        timed_out: false,
        attempts: 1,
        duration_seconds: 2.5,
        stdout: "1 passed",
        stderr: ""
      }]
    }]
  }
};

const draftPdfSubmission: PdfSubmission = {
  id: "pdf-submission-1",
  assignment_id: null,
  student_id: "alice",
  title: "Final essay",
  original_filename: "essay.pdf",
  size_bytes: 512,
  sha256: "a".repeat(64),
  page_count: 2,
  status: "draft",
  grade: null,
  total_score: 0,
  maximum_points: 0,
  created_by: "key:0123456789ab",
  created_at: "2026-08-18T12:00:00Z",
  updated_at: "2026-08-18T12:00:00Z",
  finalized_at: null
};

let pdfSubmission: PdfSubmission = { ...draftPdfSubmission };
let academicAssignments: AcademicAssignment[] = [];

const billingOverview: BillingOverview = {
  mode: "hosted",
  status: "active",
  entitled: true,
  customer_configured: true,
  subscription_configured: true,
  current_period_end: "2026-09-18T00:00:00Z",
  cancel_at_period_end: false,
  usage: { total_units: 12, reported_units: 10, pending_units: 2 }
};

Given("saved OpenGrader API credentials", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("opengrader.settings.v1", JSON.stringify({
      apiBaseUrl: "http://localhost:8000",
      apiKey: "e2e-key",
      theme: "light",
      locale: "en"
    }));
  });
});

Given("a deterministic grader API", async ({ page }) => {
  pdfSubmission = { ...draftPdfSubmission };
  academicAssignments = [];
  await page.route("**/api/opengrader/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    const apiPath = requestUrl.pathname.replace("/api/opengrader", "");
    let payload: unknown;

    if (apiPath === "/health") {
      payload = { status: "ok", version: "0.6.0", authentication_configured: true };
    } else if (apiPath === "/v1/billing/overview") {
      payload = billingOverview;
    } else if (apiPath === `/v1/pdf-submissions/${draftPdfSubmission.id}/document`) {
      await route.fulfill({ status: 200, contentType: "application/pdf", body: "%PDF-1.4\n%%EOF" });
      return;
    } else if (apiPath === `/v1/pdf-submissions/${draftPdfSubmission.id}/feedback.pdf`) {
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: { "Content-Disposition": "attachment; filename=feedback.pdf" },
        body: "%PDF-1.4\n%%EOF"
      });
      return;
    } else if (apiPath === `/v1/pdf-submissions/${draftPdfSubmission.id}/grade`) {
      const grade = route.request().postDataJSON() as PdfGradeRequest;
      pdfSubmission = {
        ...pdfSubmission,
        status: grade.finalized ? "finalized" : "draft",
        grade,
        total_score: grade.scores.reduce((sum, score) => sum + score.points, 0),
        maximum_points: grade.rubric.reduce((sum, criterion) => sum + criterion.max_points, 0),
        finalized_at: grade.finalized ? "2026-08-18T12:05:00Z" : null
      };
      payload = pdfSubmission;
    } else if (apiPath === `/v1/pdf-submissions/${draftPdfSubmission.id}`) {
      payload = pdfSubmission;
    } else if (apiPath === "/v1/assignments" && route.request().method() === "POST") {
      const input = route.request().postDataJSON() as Omit<AcademicAssignment, "id" | "created_by" | "created_at" | "updated_at">;
      const created: AcademicAssignment = { ...input, id: "assignment-1", created_by: "key:0123456789ab", created_at: "2026-08-19T12:00:00Z", updated_at: "2026-08-19T12:00:00Z" };
      academicAssignments.push(created);
      payload = created;
    } else if (apiPath === "/v1/assignments") {
      payload = academicAssignments;
    } else if (apiPath === "/v1/pdf-submissions" && route.request().method() === "POST") {
      payload = pdfSubmission;
    } else if (apiPath === "/v1/pdf-submissions") {
      payload = [];
    } else if (apiPath === `/v1/jobs/${completedJob.id}/result`) {
      payload = resultResponse;
    } else if (apiPath === `/v1/jobs/${completedJob.id}`) {
      payload = completedJob;
    } else if (apiPath === "/v1/audit-events") {
      payload = [
        { id: 1, occurred_at: "2026-08-17T12:00:00Z", actor: "key:0123456789ab", action: "job.created", resource_type: "job", resource_id: completedJob.id, details: {} },
        { id: 2, occurred_at: "2026-08-17T12:00:01Z", actor: "worker:local", action: "job.started", resource_type: "job", resource_id: completedJob.id, details: {} },
        { id: 3, occurred_at: "2026-08-17T12:00:05Z", actor: "worker:local", action: "job.succeeded", resource_type: "job", resource_id: completedJob.id, details: {} }
      ];
    } else if (apiPath === "/v1/jobs") {
      const limit = Number(requestUrl.searchParams.get("limit") ?? 100);
      const offset = Number(requestUrl.searchParams.get("offset") ?? 0);
      payload = jobs.slice(offset, offset + limit);
    } else {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
      return;
    }

    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });
});

When("I open the assignment workspace", async ({ page }) => {
  await page.goto("/assignments");
});

When("I create a written assignment for a course section", async ({ page }) => {
  await page.getByRole("button", { name: "New assignment" }).first().click();
  await page.getByRole("radio", { name: "Written or PDF work" }).click();
  await page.getByLabel("Institution").fill("Riverdale College");
  await page.getByLabel("Course code").fill("HIST-204");
  await page.getByLabel("Course name").fill("Modern History");
  await page.getByLabel("Academic period").fill("Fall 2026");
  await page.getByLabel("Section").fill("B");
  await page.getByLabel("Assignment name").fill("Primary source essay");
  await page.getByRole("button", { name: "Save assignment" }).click();
});

Then("the assignment is grouped by institution, course, period, and section", async ({ page }) => {
  await expect(page.getByText("Riverdale College · Fall 2026")).toBeVisible();
  await expect(page.getByRole("heading", { name: "HIST-204 · Modern History" })).toBeVisible();
  await expect(page.getByText("Section B")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Primary source essay" })).toBeVisible();
});

When("I switch the interface to Spanish", async ({ page }) => {
  await page.goto("/settings");
  await page.getByLabel("Language").selectOption("es");
  await page.getByRole("button", { name: "Save settings" }).click();
});

Then("the professor navigation is shown in Spanish", async ({ page }) => {
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByText("Asignaciones")).toBeVisible();
});

When("I open the jobs dashboard", async ({ page }) => {
  await page.goto("/jobs");
});

Then("the dashboard reports 11 total jobs", async ({ page }) => {
  const totalCard = page.getByText("Total jobs").locator("..");
  await expect(totalCard.getByText("11", { exact: true })).toBeVisible();
});

Then("the first jobs page contains 10 rows", async ({ page }) => {
  await expect(page.locator("tbody tr")).toHaveCount(10);
});

When("I move to the next jobs page", async ({ page }) => {
  await page.getByRole("button", { name: "Next page" }).click();
});

Then("the remaining job is visible", async ({ page }) => {
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.getByText("hw11.yaml")).toBeVisible();
});

When("I open the completed job", async ({ page }) => {
  await page.goto(`/jobs/${completedJob.id}`);
});

Then("I see the returned cohort totals", async ({ page }) => {
  await expect(page.getByText("8 / 10 cohort points")).toBeVisible();
  await expect(page.getByText("Students graded")).toBeVisible();
});

When("I expand the student and test results", async ({ page }) => {
  await page.getByRole("button", { name: "Expand alice results" }).click();
  await page.getByText("passes tests").click();
});

Then("I see semantic exit-code and timeout badges", async ({ page }) => {
  await expect(page.getByLabel("Exit code 0")).toBeVisible();
  await expect(page.getByLabel("Test completed before timeout")).toBeVisible();
});

Then("I can download both result formats", async ({ page }) => {
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "JSON" }).click();
  expect((await jsonDownload).suggestedFilename()).toBe("job-succeeded-results.json");

  const csvDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV" }).click();
  expect((await csvDownload).suggestedFilename()).toBe("job-succeeded-results.csv");
});

When("I open the audit trail", async ({ page }) => {
  await page.goto("/audit");
});

Then("I see the chronological job lifecycle and key fingerprint", async ({ page }) => {
  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText("created");
  await expect(rows.nth(2)).toContainText("succeeded");
  await expect(page.getByText("key:0123456789ab")).toBeVisible();
});

When("I open PDF grading", async ({ page }) => {
  await page.goto("/pdf");
});

When("I upload a two-page PDF submission", async ({ page }) => {
  await page.getByLabel("Student ID").fill("alice");
  await page.getByLabel("Assignment title").fill("Final essay");
  await page.getByLabel("PDF submission", { exact: true }).setInputFiles({
    name: "essay.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n%%EOF")
  });
  await page.getByRole("button", { name: "Upload PDF" }).click();
});

Then("I see the PDF grading workspace", async ({ page }) => {
  await expect(page).toHaveURL(`/pdf/${draftPdfSubmission.id}`);
  await expect(page.getByRole("heading", { name: "Final essay" })).toBeVisible();
  await expect(page.getByText("Rubric")).toBeVisible();
});

When("I score the rubric and add a page annotation", async ({ page }) => {
  await page.getByLabel("Criterion 1 score").fill("8.5");
  await page.getByLabel("Criterion 1 feedback").fill("Strong reasoning");
  await page.getByLabel("Annotation page").selectOption("2");
  await page.getByLabel("Horizontal position percent").fill("25");
  await page.getByLabel("Vertical position percent").fill("40");
  await page.getByLabel("Annotation comment").fill("Add a citation");
  await page.getByRole("button", { name: "Add annotation" }).click();
  await page.getByLabel("Overall feedback").fill("Good work.");
});

When("I finalize the PDF grade", async ({ page }) => {
  await page.getByRole("button", { name: "Finalize grade" }).click();
});

Then("I see the finalized rubric total", async ({ page }) => {
  await expect(page.getByText("Finalized grade")).toBeVisible();
  await expect(page.getByText("8.5 / 10")).toBeVisible();
});

Then("I can download the annotated feedback PDF", async ({ page }) => {
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download feedback PDF" }).click();
  expect((await download).suggestedFilename()).toBe("pdf-submission-1-feedback.pdf");
});

When("I open billing and usage", async ({ page }) => {
  await page.goto("/billing");
});

Then("I see an active hosted subscription", async ({ page }) => {
  await expect(page.getByText("Active subscription")).toBeVisible();
  await expect(page.getByText("Hosted grading is enabled")).toBeVisible();
  await expect(page.getByRole("button", { name: "Manage subscription" })).toBeVisible();
});

Then("I see accepted, reported, and pending usage units", async ({ page }) => {
  await expect(page.getByText("Accepted units").locator("..").locator("..")).toContainText("12");
  await expect(page.getByText("Reported to Stripe").locator("..").locator("..")).toContainText("10");
  await expect(page.getByText("Pending delivery").locator("..").locator("..")).toContainText("2");
});
