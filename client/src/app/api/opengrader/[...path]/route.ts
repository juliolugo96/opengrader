import type { NextRequest } from "next/server";

const REQUEST_TIMEOUT_MS = 30_000;

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context);
}

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

async function proxyRequest(request: NextRequest, context: RouteContext): Promise<Response> {
  const baseUrl = request.headers.get("x-opengrader-base-url");
  if (!baseUrl) return Response.json({ detail: "OpenGrader API URL is missing" }, { status: 400 });

  let target: URL;
  try {
    const configured = new URL(baseUrl);
    assertAllowedTarget(configured);
    const { path } = await context.params;
    target = new URL(`/${path.map(encodeURIComponent).join("/")}`, configured);
    target.search = request.nextUrl.search;
  } catch (error) {
    return Response.json(
      { detail: error instanceof Error ? error.message : "Invalid OpenGrader API URL" },
      { status: 400 }
    );
  }

  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  const contentType = request.headers.get("content-type");
  if (authorization) headers.set("Authorization", authorization);
  if (contentType) headers.set("Content-Type", contentType);

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" ? undefined : await request.text(),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store"
      }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "OpenGrader is unreachable";
    return Response.json({ detail: message }, { status: 502 });
  }
}

function assertAllowedTarget(target: URL): void {
  if (!['http:', 'https:'].includes(target.protocol)) {
    throw new Error("API URL must use HTTP or HTTPS");
  }
  if (target.username || target.password) {
    throw new Error("API URL cannot contain credentials");
  }
  const allowedHosts = (process.env.OPENGRADER_ALLOWED_HOSTS ?? "localhost,127.0.0.1")
    .split(",")
    .map((host) => host.trim().toLowerCase())
    .filter(Boolean);
  if (!allowedHosts.includes(target.hostname.toLowerCase())) {
    throw new Error("API host is not allowed by this dashboard deployment");
  }
}
