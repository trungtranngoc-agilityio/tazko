import { vi } from "vitest";

export type Reply = { status: number; body?: unknown };
type Route = Reply | "hang" | ((body: unknown, query: URLSearchParams) => Reply | Promise<Reply>);
export type Call = { method: string; path: string; query: URLSearchParams; body: unknown };

/** A fake API: answers by "METHOD path" (no query string); anything else is a
 * 404. "hang" never answers (a slow load); a route may answer later through a
 * promise. Records every call. */
export function fakeApi(routes: Record<string, Route>): Call[] {
  const calls: Call[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const parsed = new URL(url, "http://web");
    const path = parsed.pathname;
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, query: parsed.searchParams, body });
    const route = routes[`${method} ${path}`];
    if (route === "hang") return new Promise<Response>(() => {});
    const reply = await (typeof route === "function"
      ? route(body, parsed.searchParams)
      : (route ?? { status: 404, body: apiError("NOT_FOUND") }));
    return new Response(reply.status === 204 ? null : JSON.stringify(reply.body), {
      status: reply.status,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

/** An error body as the API sends it. */
export function apiError(code: string) {
  return { error: { code, message: code.toLowerCase(), details: [] } };
}
