import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SignInPage } from "@/pages/signin/SignInPage";
import { AdminLayout } from "./AdminLayout";
import { AppLayout } from "./AppLayout";

const ME = { id: 1, email: "ana@example.com", name: "Ana", avatar_url: null, is_super_admin: true };

function reply(status: number, body: unknown): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function error(status: number, code: string): Response {
  return reply(status, { error: { code, message: code.toLowerCase(), details: [] } });
}

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<p>Home page</p>} />
        </Route>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<p>Admin page</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe.each([
  ["/", "Home page"],
  ["/admin", "Admin page"],
])("the %s shell", (path, page) => {
  it("sends a visitor without a session to sign in", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(error(401, "UNAUTHENTICATED")));

    show(path);

    expect(await screen.findByRole("heading", { name: "Sign in to Tazko" })).toBeInTheDocument();
    expect(screen.queryByText(page)).not.toBeInTheDocument();
  });

  it("shows the page to a signed-in person", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(200, ME)));

    show(path);

    expect(await screen.findByText(page)).toBeInTheDocument();
  });
});

describe("loading the session", () => {
  it("says it is loading while the API answers", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    show("/");

    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("explains a server error and loads again on Retry", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(error(503, "INTERNAL"))
      .mockResolvedValueOnce(reply(200, ME));
    vi.stubGlobal("fetch", fetchMock);

    show("/");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong on our side. Try again.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Home page")).toBeInTheDocument();
  });

  it("explains when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    show("/");

    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong. Try again.");
  });
});

describe("Sign out", () => {
  it("ends the session and goes to sign in", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(200, ME))
      .mockResolvedValueOnce(reply(204, null));
    vi.stubGlobal("fetch", fetchMock);
    show("/");

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith("/signin"));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/auth/signout",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });

  it("says so when sign-out is refused", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(reply(200, ME)).mockResolvedValueOnce(error(403, "FORBIDDEN")),
    );
    show("/");

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have access to this.");
    expect(assign).not.toHaveBeenCalled();
  });
});
