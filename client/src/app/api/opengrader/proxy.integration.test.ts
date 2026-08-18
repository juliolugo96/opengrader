import { describe, expect, it, vi } from "vitest";

import { GET, POST, PUT } from "@/app/api/opengrader/[...path]/route";

describe("OpenGrader same-origin proxy", () => {
  it("forwards pagination and bearer authentication to an allowed backend", async () => {
    const backendFetch = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } })
    );
    vi.stubGlobal("fetch", backendFetch);
    const request = {
      method: "GET",
      headers: new Headers({
        Authorization: "Bearer secret",
        "X-OpenGrader-Base-URL": "http://localhost:8000"
      }),
      nextUrl: new URL("http://localhost:3000/api/opengrader/v1/jobs?limit=10&offset=20")
    } as never;

    const response = await GET(request, { params: Promise.resolve({ path: ["v1", "jobs"] }) });

    expect(response.status).toBe(200);
    expect(String(backendFetch.mock.calls[0][0])).toBe("http://localhost:8000/v1/jobs?limit=10&offset=20");
    expect(new Headers(backendFetch.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer secret");
  });

  it.each([
    ["POST", POST],
    ["PUT", PUT]
  ] as const)("forwards %s request bytes without corrupting PDF or multipart bodies", async (method, handler) => {
    const responseBytes = new Uint8Array([37, 80, 68, 70]);
    const backendFetch = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(responseBytes, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": "attachment; filename=feedback.pdf"
        }
      })
    );
    vi.stubGlobal("fetch", backendFetch);
    const requestBytes = new Uint8Array([0, 255, 1, 2]);
    const request = {
      method,
      headers: new Headers({
        Authorization: "Bearer secret",
        "Content-Type": "multipart/form-data; boundary=test",
        "X-OpenGrader-Base-URL": "http://localhost:8000"
      }),
      nextUrl: new URL("http://localhost:3000/api/opengrader/v1/pdf-submissions"),
      arrayBuffer: async () => requestBytes.buffer
    } as never;

    const response = await handler(request, { params: Promise.resolve({ path: ["v1", "pdf-submissions"] }) });

    expect(new Uint8Array(backendFetch.mock.calls[0][1]?.body as ArrayBuffer)).toEqual(requestBytes);
    expect(response.headers.get("content-disposition")).toBe("attachment; filename=feedback.pdf");
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(responseBytes);
  });
});
