import { api, ApiError } from "./client";

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the session cookie cross-origin", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" })));
    vi.stubGlobal("fetch", fetchMock);

    await api("/health");

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ credentials: "include" });
  });

  it("turns an error body into ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify({ error: "not allowed" }), { status: 403 })),
    );

    await expect(api("/x")).rejects.toEqual(new ApiError(403, "not allowed"));
  });
});
