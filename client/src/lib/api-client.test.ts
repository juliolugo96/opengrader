import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createJob, listJobs } from "@/lib/api-client";
import { saveSettings } from "@/lib/storage";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  saveSettings({ apiBaseUrl: "http://localhost:8000", apiKey: "secret-key", theme: "dark" });
});

describe("API client", () => {
  it("attaches proxy routing and bearer credentials", async () => {
    fetchMock.mockResolvedValue(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));

    await listJobs({ status: "running", limit: 25 });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opengrader/v1/jobs?status=running&limit=25");
    const headers = new Headers(options?.headers);
    expect(headers.get("Authorization")).toBe("Bearer secret-key");
    expect(headers.get("X-OpenGrader-Base-URL")).toBe("http://localhost:8000");
  });

  it("maps the dashboard job form to the current backend contract", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 202, headers: { "Content-Type": "application/json" } }));

    await createJob({
      assignmentPath: "assignments/hw1.yaml",
      submissionsDirectory: "submissions",
      workers: 4,
      retries: 1,
      submissionFilter: "section-a-*",
      noDocker: false
    });

    const options = fetchMock.mock.calls[0][1];
    expect(JSON.parse(String(options?.body))).toEqual({
      assignment_file: "assignments/hw1.yaml",
      submissions_dir: "submissions",
      workers: 4,
      retries: 1,
      submission_patterns: ["section-a-*"],
      no_docker: false
    });
  });

  it("surfaces backend detail as a typed error", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"Invalid API key"}', { status: 401, headers: { "Content-Type": "application/json" } }));

    await expect(listJobs()).rejects.toEqual(expect.objectContaining<ApiError>({
      name: "ApiError",
      message: "Invalid API key",
      status: 401
    }));
  });
});
