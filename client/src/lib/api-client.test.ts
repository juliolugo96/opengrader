import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createBillingCheckout,
  createBillingPortal,
  createJob,
  getPdfDocument,
  getPdfFeedback,
  getPdfSubmission,
  getBillingOverview,
  listAllPdfSubmissions,
  listAllJobs,
  listJobs,
  listPdfSubmissions,
  savePdfGrade,
  testConnection,
  uploadPdfSubmission
} from "@/lib/api-client";
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

    await listJobs({ status: "running", limit: 25, offset: 50 });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opengrader/v1/jobs?status=running&limit=25&offset=50");
    const headers = new Headers(options?.headers);
    expect(headers.get("Authorization")).toBe("Bearer secret-key");
    expect(headers.get("X-OpenGrader-Base-URL")).toBe("http://localhost:8000");
    expect(options?.cache).toBe("no-store");
  });

  it("keeps health public while authenticating the readiness probe", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response('{"status":"ok","version":"0.6.0","authentication_configured":true}', { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));

    const health = await testConnection({
      apiBaseUrl: "https://override.example",
      apiKey: "override-key",
      theme: "light"
    });

    expect(health.version).toBe("0.6.0");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/opengrader/health",
      "/api/opengrader/v1/jobs?limit=1"
    ]);
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Authorization")).toBeNull();
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("X-OpenGrader-Base-URL")).toBe("https://override.example");
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("Authorization")).toBe("Bearer override-key");
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("X-OpenGrader-Base-URL")).toBe("https://override.example");
  });

  it("maps the dashboard job form to the current backend contract", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 202, headers: { "Content-Type": "application/json" } }));

    await createJob({
      assignmentPath: "assignments/hw1.yaml",
      submissionsDirectory: "submissions",
      workers: 4,
      retries: 1,
      submissionFilter: " section-a-* ",
      noDocker: false
    });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opengrader/v1/jobs");
    expect(options?.method).toBe("POST");
    expect(new Headers(options?.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(options?.body))).toEqual({
      assignment_path: "assignments/hw1.yaml",
      submissions_dir: "submissions",
      workers: 4,
      retries: 1,
      submission_filter: "section-a-*",
      no_docker: false
    });
  });

  it("loads billing state and creates server-owned checkout and portal sessions", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response('{"mode":"hosted","status":"none"}', { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response('{"url":"https://checkout.stripe.test/session"}', { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response('{"url":"https://billing.stripe.test/portal"}', { status: 200, headers: { "Content-Type": "application/json" } }));

    await getBillingOverview();
    await createBillingCheckout(" teacher@example.com ");
    await createBillingPortal();

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/opengrader/v1/billing/overview",
      "/api/opengrader/v1/billing/checkout",
      "/api/opengrader/v1/billing/portal"
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      email: "teacher@example.com"
    });
    expect(fetchMock.mock.calls[1][1]?.method).toBe("POST");
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("Content-Type")).toBe("application/json");
    expect(fetchMock.mock.calls[2][1]?.method).toBe("POST");
  });

  it("loads every jobs page so dashboard totals are complete", async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({ id: `job-${index}` }));
    const secondPage = [{ id: "job-100" }];
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify(firstPage), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(secondPage), { status: 200, headers: { "Content-Type": "application/json" } }));

    const jobs = await listAllJobs();

    expect(jobs).toHaveLength(101);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/opengrader/v1/jobs?limit=100&offset=0",
      "/api/opengrader/v1/jobs?limit=100&offset=100"
    ]);
  });

  it("surfaces backend detail as a typed error", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"Invalid API key"}', { status: 401, headers: { "Content-Type": "application/json" } }));

    await expect(listJobs()).rejects.toEqual(expect.objectContaining<ApiError>({
      name: "ApiError",
      message: "Invalid API key",
      status: 401
    }));
  });

  it("uploads PDF metadata and bytes as multipart form data", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 201, headers: { "Content-Type": "application/json" } }));
    const file = new File(["%PDF-test"], "paper.pdf", { type: "application/pdf" });

    await uploadPdfSubmission({ file, studentId: " alice ", title: " Research paper " });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opengrader/v1/pdf-submissions");
    expect(options?.method).toBe("POST");
    expect(new Headers(options?.headers).has("Content-Type")).toBe(false);
    const form = options?.body as FormData;
    expect(form.get("student_id")).toBe("alice");
    expect(form.get("title")).toBe("Research paper");
    expect(form.get("file")).toBe(file);
  });

  it("loads every PDF submissions page and addresses individual records", async () => {
    const firstPage = Array.from({ length: 100 }, (_, index) => ({ id: `pdf-${index}` }));
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify(firstPage), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response('[{"id":"pdf-100"}]', { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response('{"id":"pdf-100"}', { status: 200, headers: { "Content-Type": "application/json" } }));

    const submissions = await listAllPdfSubmissions();
    const submission = await getPdfSubmission("pdf 100");

    expect(submissions).toHaveLength(101);
    expect(submission.id).toBe("pdf-100");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/opengrader/v1/pdf-submissions?limit=100&offset=0",
      "/api/opengrader/v1/pdf-submissions?limit=100&offset=100",
      "/api/opengrader/v1/pdf-submissions/pdf%20100"
    ]);
  });

  it("passes explicit PDF listing boundaries", async () => {
    fetchMock.mockResolvedValue(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));

    expect(await listPdfSubmissions({ limit: 25, offset: 50 })).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/opengrader/v1/pdf-submissions?limit=25&offset=50");
  });

  it("saves the complete rubric and annotation contract", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    const grade = {
      rubric: [{ id: "analysis", title: "Analysis", description: "", max_points: 10 }],
      scores: [{ criterion_id: "analysis", points: 8, feedback: "Good" }],
      annotations: [{ page: 1, x: 0.2, y: 0.3, comment: "Clarify" }],
      overall_feedback: "Well done",
      finalized: true
    };

    await savePdfGrade("pdf 1", grade);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/opengrader/v1/pdf-submissions/pdf%201/grade");
    expect(options?.method).toBe("PUT");
    expect(new Headers(options?.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(options?.body))).toEqual(grade);
  });

  it("returns PDF responses as binary blobs", async () => {
    fetchMock.mockResolvedValue(new Response("%PDF-test", { status: 200, headers: { "Content-Type": "application/pdf" } }));

    const blob = await getPdfDocument("pdf-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/opengrader/v1/pdf-submissions/pdf-1/document");
    expect(blob.type).toBe("application/pdf");
    expect(blob.size).toBe(9);
  });

  it("downloads finalized feedback from the encoded PDF resource", async () => {
    fetchMock.mockResolvedValue(new Response("%PDF", { status: 200, headers: { "Content-Type": "application/pdf" } }));

    const blob = await getPdfFeedback("pdf 1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/opengrader/v1/pdf-submissions/pdf%201/feedback.pdf");
    expect(blob.type).toBe("application/pdf");
  });

  it("maps text, structured, and empty backend failures", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response("Gateway unavailable", { status: 502, headers: { "Content-Type": "text/plain" } }))
      .mockResolvedValueOnce(new Response('{"detail":{"field":"bad"}}', { status: 422, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response("{}", { status: 418, headers: { "Content-Type": "application/json" } }));

    await expect(listJobs()).rejects.toMatchObject({ message: "Gateway unavailable", status: 502 });
    await expect(listJobs()).rejects.toMatchObject({ message: '{"field":"bad"}', status: 422 });
    await expect(listJobs()).rejects.toMatchObject({ message: "OpenGrader returned 418", status: 418 });
  });

  it("wraps network failures without exposing an untyped exception", async () => {
    fetchMock.mockRejectedValue(new Error("socket closed"));

    await expect(listJobs()).rejects.toMatchObject({ message: "socket closed", status: 0 });
  });

  it("uses safe fallbacks for non-error network failures and null error payloads", async () => {
    fetchMock.mockRejectedValueOnce("offline");
    await expect(listJobs()).rejects.toMatchObject({ message: "Could not reach OpenGrader", status: 0 });

    fetchMock
      .mockResolvedValueOnce(new Response("null", { status: 500, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response("42", { status: 500, headers: { "Content-Type": "application/json" } }));
    await expect(listJobs()).rejects.toMatchObject({ message: "OpenGrader returned 500", status: 500 });
    await expect(listJobs()).rejects.toMatchObject({ message: "OpenGrader returned 500", status: 500 });
  });

  it("treats a successful response without a content type as text", async () => {
    fetchMock.mockResolvedValue(new Response(new TextEncoder().encode("plain response"), { status: 200 }));

    expect(await listJobs()).toBe("plain response");
  });
});
