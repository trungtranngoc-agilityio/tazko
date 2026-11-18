import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyHomePage } from "@/pages/company/CompanyHomePage";
import { CompanySettingsPage } from "@/pages/company/CompanySettingsPage";
import { HomePage } from "@/pages/home/HomePage";
import { AppLayout } from "./AppLayout";
import { CompanyLayout } from "./CompanyLayout";

const ANA = {
  id: 1,
  email: "ana@harbor.vn",
  name: "Ana Tran",
  avatar_url: null,
  is_super_admin: false,
};
const HARBOR = { slug: "harbor", name: "Harbor Studio", role: "owner", status: "active" };
const NORTH = { slug: "north", name: "Northwind Labs", role: "member", status: "active" };
const LARK = { slug: "lark", name: "Larkspur Co", role: "member", status: "suspended" };
const MEMBERS = [
  {
    user_id: 1,
    name: "Ana Tran",
    email: "ana@harbor.vn",
    avatar_url: null,
    account: "workspace",
    role: "owner",
    last_seen_at: new Date().toISOString(),
  },
  {
    user_id: 2,
    name: "Bo Le",
    email: "bo@gmail.com",
    avatar_url: null,
    account: "personal",
    role: "member",
    last_seen_at: null,
  },
];
const INVITES = [
  {
    id: 7,
    email: "cy@gmail.com",
    role: "member",
    account: "personal",
    invited_by: "Ana Tran",
    created_at: "2026-11-05T10:00:00.000Z",
    expires_at: "2026-11-19T10:00:00.000Z",
  },
];

type Reply = { status: number; body?: unknown };

/** A fake API: answers by "METHOD path"; anything else is a 404. Records every call. */
function fakeApi(routes: Record<string, Reply | ((body: unknown) => Reply)>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const path = new URL(url, "http://web").pathname;
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body });
    const route = routes[`${method} ${path}`];
    const reply =
      typeof route === "function"
        ? route(body)
        : (route ?? { status: 404, body: error("NOT_FOUND") });
    return new Response(reply.status === 204 ? null : JSON.stringify(reply.body), {
      status: reply.status,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

function error(code: string) {
  return { error: { code, message: code.toLowerCase(), details: [] } };
}

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/signin" element={<p>Sign in page</p>} />
        <Route path="/admin" element={<p>Admin console</p>} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<HomePage />} />
        </Route>
        <Route path="/c/:slug" element={<CompanyLayout />}>
          <Route index element={<CompanyHomePage />} />
          <Route path="settings" element={<CompanySettingsPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

const SIGNED_IN = {
  "GET /api/me": { status: 200, body: ANA },
  "GET /api/orgs": { status: 200, body: [HARBOR, NORTH, LARK] },
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("home", () => {
  it("opens the person's first active company", async () => {
    fakeApi(SIGNED_IN);

    show("/");

    expect(await screen.findByRole("heading", { name: "Projects" })).toBeInTheDocument();
    expect(
      screen.getByText(/Harbor Studio · you see the projects you belong to/),
    ).toBeInTheDocument();
  });

  it("explains when the person is in no company", async () => {
    fakeApi({ ...SIGNED_IN, "GET /api/orgs": { status: 200, body: [] } });

    show("/");

    expect(await screen.findByText("You are not in a company yet")).toBeInTheDocument();
  });
});

describe("company switcher", () => {
  it("lists only the person's companies and switches", async () => {
    fakeApi(SIGNED_IN);
    show("/c/harbor");

    fireEvent.click(await screen.findByRole("button", { name: /Harbor Studio/ }));
    const menu = screen.getByRole("menu");
    expect(
      within(menu)
        .getAllByRole("menuitem")
        .map((i) => i.textContent),
    ).toEqual([
      expect.stringContaining("Harbor Studio"),
      expect.stringContaining("Northwind Labs"),
      expect.stringContaining("Larkspur Co"),
    ]);
    expect(within(menu).getByRole("menuitem", { name: /Larkspur Co/ })).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    fireEvent.click(within(menu).getByRole("menuitem", { name: /Northwind Labs/ }));

    expect(
      await screen.findByText(/Northwind Labs · you see the projects you belong to/),
    ).toBeInTheDocument();
  });

  it("shows Company settings to owners only", async () => {
    fakeApi(SIGNED_IN);
    show("/c/north");

    await screen.findByText(/Northwind Labs · you see/);
    expect(screen.queryByRole("link", { name: "Company settings" })).not.toBeInTheDocument();
  });

  it("offers the admin console to super admins only", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /api/me": { status: 200, body: { ...ANA, is_super_admin: true } },
    });
    show("/c/harbor");

    expect(await screen.findByRole("link", { name: "Admin console" })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("says when the company is not one of the person's", async () => {
    fakeApi(SIGNED_IN);

    show("/c/other");

    expect(
      await screen.findByText("This no longer exists, or you do not have access to it."),
    ).toBeInTheDocument();
  });
});

describe("company settings", () => {
  const SETTINGS = {
    ...SIGNED_IN,
    "GET /api/orgs/harbor/members": { status: 200, body: MEMBERS },
    "GET /api/orgs/harbor/invites": { status: 200, body: INVITES },
  };

  it("lists members and pending invites", async () => {
    fakeApi(SETTINGS);

    show("/c/harbor/settings");

    const members = await screen.findByRole("table", { name: "Members" });
    expect(within(members).getByText("bo@gmail.com")).toBeInTheDocument();
    expect(within(members).getByText("Workspace")).toBeInTheDocument();
    expect(within(members).getByText("Personal Gmail")).toBeInTheDocument();
    expect(within(members).getByText("Never")).toBeInTheDocument();
    const invites = screen.getByRole("table", { name: "Pending invites" });
    expect(within(invites).getByText("cy@gmail.com")).toBeInTheDocument();
    expect(within(invites).getByText("Ana Tran")).toBeInTheDocument();
  });

  it("invites someone and tells the owner to share the address", async () => {
    const calls = fakeApi({
      ...SETTINGS,
      "POST /api/orgs/harbor/invites": {
        status: 201,
        body: { ...INVITES[0], id: 8, email: "di@harbor.vn", role: "owner", account: null },
      },
    });
    show("/c/harbor/settings");

    fireEvent.change(await screen.findByRole("textbox", { name: "Email" }), {
      target: { value: "di@harbor.vn" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Role" }), {
      target: { value: "owner" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    expect(await screen.findByText(/Invited di@harbor.vn/)).toHaveAttribute("role", "status");
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      email: "di@harbor.vn",
      role: "owner",
    });
  });

  it("explains a refused invite", async () => {
    fakeApi({
      ...SETTINGS,
      "POST /api/orgs/harbor/invites": { status: 409, body: error("ALREADY_MEMBER") },
    });
    show("/c/harbor/settings");

    fireEvent.change(await screen.findByRole("textbox", { name: "Email" }), {
      target: { value: "bo@gmail.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This person is already a member of the company.",
    );
  });

  it("changes a role", async () => {
    const calls = fakeApi({
      ...SETTINGS,
      "PATCH /api/orgs/harbor/members/2": { status: 200, body: { ...MEMBERS[1], role: "owner" } },
    });
    show("/c/harbor/settings");

    fireEvent.change(await screen.findByRole("combobox", { name: "Role of Bo Le" }), {
      target: { value: "owner" },
    });

    await waitFor(() => expect(calls.some((c) => c.method === "PATCH")).toBe(true));
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ role: "owner" });
  });

  it("says the last owner must stay", async () => {
    fakeApi({
      ...SETTINGS,
      "PATCH /api/orgs/harbor/members/1": { status: 409, body: error("LAST_OWNER") },
    });
    show("/c/harbor/settings");

    fireEvent.change(await screen.findByRole("combobox", { name: "Role of Ana Tran" }), {
      target: { value: "member" },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A company needs at least one owner.",
    );
  });

  it("asks before removing someone and does nothing on Cancel", async () => {
    // KNOWN-DEVIATIONS #5: the prototype removes at once.
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const calls = fakeApi(SETTINGS);
    show("/c/harbor/settings");

    fireEvent.click(await screen.findByRole("button", { name: "Remove Bo Le" }));

    expect(confirm).toHaveBeenCalledWith("Remove Bo Le from Harbor Studio?");
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
  });

  it("removes someone after the owner confirms", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const calls = fakeApi({ ...SETTINGS, "DELETE /api/orgs/harbor/members/2": { status: 204 } });
    show("/c/harbor/settings");

    fireEvent.click(await screen.findByRole("button", { name: "Remove Bo Le" }));

    await waitFor(() => expect(calls.some((c) => c.method === "DELETE")).toBe(true));
  });

  it("warns harder when an owner removes themselves, then leaves the company", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    fakeApi({ ...SETTINGS, "DELETE /api/orgs/harbor/members/1": { status: 204 } });
    show("/c/harbor/settings");

    fireEvent.click(await screen.findByRole("button", { name: "Remove Ana Tran" }));

    expect(confirm).toHaveBeenCalledWith(
      "Remove yourself from Harbor Studio? You will lose access to it.",
    );
    expect(await screen.findByRole("heading", { name: "Projects" })).toBeInTheDocument();
  });

  it("revokes an invite", async () => {
    const calls = fakeApi({ ...SETTINGS, "DELETE /api/orgs/harbor/invites/7": { status: 204 } });
    show("/c/harbor/settings");

    fireEvent.click(await screen.findByRole("button", { name: "Revoke cy@gmail.com" }));

    await waitFor(() =>
      expect(calls.some((c) => c.path === "/api/orgs/harbor/invites/7")).toBe(true),
    );
  });

  it("shows a member that only owners manage the company", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /api/orgs/north/members": { status: 403, body: error("FORBIDDEN") },
    });

    show("/c/north/settings");

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have access to this.");
  });
});
