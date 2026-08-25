import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

Given("credentials for the isolated platform API", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("opengrader.settings.v1", JSON.stringify({
      apiBaseUrl: "http://127.0.0.1:8100",
      apiKey: "platform-e2e-key",
      theme: "light",
      locale: "en"
    }));
  });
});

When("I create a persisted written assignment through the platform", async ({ page }) => {
  await page.goto("/assignments");
  const createButton = page.getByRole("button", { name: "New assignment" }).first();
  await expect(createButton).toBeEnabled();
  await createButton.click();
  await page.getByRole("radio", { name: "Written or PDF work" }).click();
  await page.getByLabel("Institution").fill("Northstar University");
  await page.getByLabel("Course code").fill("WRIT-210");
  await page.getByLabel("Course name").fill("Research Writing");
  await page.getByLabel("Academic period").fill("Spring 2027");
  await page.getByLabel("Section").fill("C");
  await page.getByLabel("Assignment name").fill("Evidence synthesis");
  await page.getByRole("button", { name: "Save assignment" }).click();
  await expect(page.getByRole("heading", { name: "Evidence synthesis" })).toBeVisible();
});

Then("the assignment remains visible after a browser reload", async ({ page }) => {
  await page.reload();
  await expect(page.getByRole("heading", { name: "Evidence synthesis" })).toBeVisible();
  await expect(page.getByText("Northstar University · Spring 2027")).toBeVisible();
  await expect(page.getByRole("heading", { name: "WRIT-210 · Research Writing" })).toBeVisible();
  await expect(page.getByText("Section C")).toBeVisible();
});

Then("the real audit trail records the assignment creation", async ({ page }) => {
  await page.goto("/audit");
  const row = page.locator("tbody tr").filter({ hasText: "academic assignment created" });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("key:");
});
