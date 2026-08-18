import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

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

Given("saved OpenGrader API credentials", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("opengrader.settings.v1", JSON.stringify({
      apiBaseUrl: "http://localhost:8000",
      apiKey: "e2e-key",
      theme: "light"
    }));
  });
});

Given("a deterministic grader API", async ({ page }) => {
  await page.route("**/api/opengrader/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    const apiPath = requestUrl.pathname.replace("/api/opengrader", "");
    let payload: unknown;

    if (apiPath === "/health") {
      payload = { status: "ok", version: "0.4.0", authentication_configured: true };
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
