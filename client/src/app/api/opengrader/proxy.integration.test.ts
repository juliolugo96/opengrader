import { describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/opengrader/[...path]/route";

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
});
