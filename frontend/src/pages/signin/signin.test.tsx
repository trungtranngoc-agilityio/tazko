import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RequireSession } from "@/features/auth";
import { RefusedPage } from "./RefusedPage";
import { SignInPage } from "./SignInPage";

function answer(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/signin/refused" element={<RefusedPage />} />
        <Route
          path="/"
          element={
            <RequireSession>
              <p>Signed-in home</p>
            </RequireSession>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("Sign in", () => {
  it("starts Google sign-in on the API host", () => {
    show("/signin");

    expect(screen.getByRole("heading", { name: "Sign in to Tazko" })).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Continue with Google" });
    expect(link.getAttribute("href")).toMatch(/\/auth\/google\/start$/);
    expect(screen.getByText(/Access is by invitation only/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says when the last sign-in did not finish", () => {
    show("/signin?error=failed");

    expect(screen.getByRole("alert")).toHaveTextContent("Sign-in did not finish");
  });
});

describe("Sign-in refused", () => {
  it("names the refused account and offers another one", async () => {
    answer(200, { email: "jo.lee@gmail.com" });

    show("/signin/refused");

    expect(await screen.findByText("jo.lee@gmail.com")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "This account is not invited" }),
    ).toBeInTheDocument();
    const retry = screen.getByRole("link", { name: "Try another Google account" });
    expect(retry.getAttribute("href")).toMatch(/\/auth\/google\/start$/);
  });

  it("tells a member that their company is suspended", async () => {
    answer(200, { email: "ana@harbor.vn", reason: "company_suspended" });

    show("/signin/refused");

    expect(
      await screen.findByRole("heading", { name: "Your company is suspended" }),
    ).toBeInTheDocument();
    expect(screen.getByText("ana@harbor.vn")).toBeInTheDocument();
    expect(screen.getByText(/ask a super admin of Tazko to resume it/)).toBeInTheDocument();
  });

  it("still explains the refusal when the account is no longer known", async () => {
    answer(404, { error: { code: "NOT_FOUND", message: "not found", details: [] } });

    show("/signin/refused");

    expect(
      await screen.findByText("This Google account is not on the list for Tazko."),
    ).toBeInTheDocument();
  });
});

describe("RequireSession", () => {
  it("sends a visitor without a session to sign in", async () => {
    answer(401, { error: { code: "UNAUTHENTICATED", message: "sign in required", details: [] } });

    show("/");

    expect(await screen.findByRole("heading", { name: "Sign in to Tazko" })).toBeInTheDocument();
    expect(screen.queryByText("Signed-in home")).not.toBeInTheDocument();
  });

  it("shows the page to a signed-in person", async () => {
    const fetchMock = answer(200, {
      id: 1,
      email: "ana@example.com",
      name: "Ana",
      avatar_url: null,
      is_super_admin: false,
    });

    show("/");

    expect(await screen.findByText("Signed-in home")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
