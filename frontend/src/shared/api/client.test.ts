import { api, ApiError } from "./client";

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the session cookie cross-origin", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" })));
    vi.stubGlobal("fetch", fetchMock);

    await api("/health");

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ credentials: "include" });
  });

  it("turns an error body into ApiError with its code and details", async () => {
    const error = {
      code: "SLUG_TAKEN",
      message: "slug: already taken",
      details: [{ field: "slug", message: "already taken" }],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ error }), { status: 409 })),
    );

    const thrown = await api("/x").catch((e: unknown) => e);

    expect(thrown).toBeInstanceOf(ApiError);
    expect(thrown).toMatchObject({
      status: 409,
      code: "SLUG_TAKEN",
      message: "slug: already taken",
      details: [{ field: "slug", message: "already taken" }],
    });
  });

  it("gives a code even when the body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response("Bad gateway", { status: 502, statusText: "Bad Gateway" })),
    );

    await expect(api("/x")).rejects.toMatchObject({ status: 502, code: "HTTP_502", details: [] });
  });
});
