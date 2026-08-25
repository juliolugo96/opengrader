import { defineConfig } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

const testDir = defineBddConfig({
  features: "e2e/features/**/*.feature",
  steps: "e2e/steps/**/*.ts",
  outputDir: ".features-gen"
});

export default defineConfig({
  testDir,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3100",
    screenshot: "only-on-failure",
    trace: "retain-on-failure"
  },
  webServer: [
    {
      command: "../.venv/bin/python e2e/support/start_api.py",
      url: "http://127.0.0.1:8100/health",
      reuseExistingServer: false,
      timeout: 120_000
    },
    {
      command: "npm run start:standalone",
      url: "http://127.0.0.1:3100/jobs",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000
    }
  ]
});
