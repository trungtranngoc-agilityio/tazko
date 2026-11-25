import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyHomePage } from "@/pages/company/CompanyHomePage";
import { CompanySettingsPage } from "@/pages/company/CompanySettingsPage";
import { HomePage } from "@/pages/home/HomePage";
import { apiError as error, fakeApi } from "@/test/fakeApi";
import { AppLayout } from "@/app/layouts/AppLayout";
import { CompanyLayout } from "@/app/layouts/CompanyLayout";

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

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Link to="/c/north/settings">go to north settings</Link>
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

  it("shows the prototype's icons on the sidebar links", async () => {
    fakeApi(SIGNED_IN);
    show("/c/harbor");

    await screen.findByText(/Harbor Studio · you see/);

    expect(screen.getByRole("link", { name: "Projects" }).querySelector("svg")).toHaveAttribute(
      "data-icon",
      "grid",
    );
    expect(
      screen.getByRole("link", { name: "Company settings" }).querySelector("svg"),
    ).toHaveAttribute("data-icon", "gear");
  });

  it("shows the prototype's icons in the switcher", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /api/me": { status: 200, body: { ...ANA, is_super_admin: true } },
    });
    show("/c/harbor");
    const button = await screen.findByRole("button", { name: /Harbor Studio/ });
    expect(button.querySelector("svg")).toHaveAttribute("data-icon", "chev");

    fireEvent.click(button);

    const current = screen.getByRole("menuitem", { name: /Harbor Studio/ });
    expect(current.querySelector("svg")).toHaveAttribute("data-icon", "check");
    expect(
      screen.getByRole("menuitem", { name: "Admin console" }).querySelector("svg"),
    ).toHaveAttribute("data-icon", "shield");
  });

  it("shows Company settings to owners only", async () => {
    fakeApi(SIGNED_IN);
    show("/c/north");

    await screen.findByText(/Northwind Labs · you see/);
    expect(screen.queryByRole("link", { name: "Company settings" })).not.toBeInTheDocument();
  });

  it("offers the admin console in the menu to super admins only", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /api/me": { status: 200, body: { ...ANA, is_super_admin: true } },
    });
    show("/c/harbor");

    fireEvent.click(await screen.findByRole("button", { name: /Harbor Studio/ }));

    expect(screen.getByRole("menuitem", { name: "Admin console" })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("hides the admin console from others", async () => {
    fakeApi(SIGNED_IN);
    show("/c/harbor");

    fireEvent.click(await screen.findByRole("button", { name: /Harbor Studio/ }));

    expect(screen.queryByRole("menuitem", { name: "Admin console" })).not.toBeInTheDocument();
  });

  it("closes the menu with Escape and gives focus back", async () => {
    fakeApi(SIGNED_IN);
    show("/c/harbor");
    const button = await screen.findByRole("button", { name: /Harbor Studio/ });

    fireEvent.click(button);
    expect(screen.getByRole("menuitem", { name: /Harbor Studio/ })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });

  it("closes the menu on a click outside", async () => {
    fakeApi(SIGNED_IN);
    show("/c/harbor");
    fireEvent.click(await screen.findByRole("button", { name: /Harbor Studio/ }));

    fireEvent.mouseDown(document.body);

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("says a suspended company is suspended", async () => {
    fakeApi(SIGNED_IN);

    show("/c/lark");

    expect(await screen.findByRole("alert")).toHaveTextContent("This company is suspended");
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
    expect(
      within(members).getByRole("button", { name: "Remove Bo Le" }).querySelector("svg"),
    ).toHaveAttribute("data-icon", "x");
    expect(screen.getByRole("button", { name: "Invite" }).querySelector("svg")).toHaveAttribute(
      "data-icon",
      "plus",
    );
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

  it("changes a role and shows the role the server kept", async () => {
    let people = MEMBERS;
    const calls = fakeApi({
      ...SETTINGS,
      "GET /api/orgs/harbor/members": () => ({ status: 200, body: people }),
      "PATCH /api/orgs/harbor/members/2": () => {
        people = [MEMBERS[0]!, { ...MEMBERS[1]!, role: "owner" }];
        return { status: 200, body: people[1] };
      },
    });
    show("/c/harbor/settings");
    const select = await screen.findByRole("combobox", { name: "Role of Bo Le" });

    fireEvent.change(select, { target: { value: "owner" } });

    await waitFor(() => expect(calls.filter((c) => c.path.endsWith("/members")).length).toBe(2));
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ role: "owner" });
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Role of Bo Le" })).toHaveValue("owner"),
    );
  });

  it("puts the role back when the server refuses the change", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true); // demoting yourself asks first
    fakeApi({
      ...SETTINGS,
      "PATCH /api/orgs/harbor/members/1": { status: 409, body: error("LAST_OWNER") },
    });
    show("/c/harbor/settings");

    fireEvent.change(await screen.findByRole("combobox", { name: "Role of Ana Tran" }), {
      target: { value: "member" },
    });

    await screen.findByRole("alert");
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Role of Ana Tran" })).toHaveValue("owner"),
    );
  });

  it("leaves Company settings when the owner makes themselves a member", async () => {
    let companies = [HARBOR, NORTH, LARK];
    vi.spyOn(window, "confirm").mockReturnValue(true);
    fakeApi({
      ...SETTINGS,
      "GET /api/orgs": () => ({ status: 200, body: companies }),
      "PATCH /api/orgs/harbor/members/1": () => {
        companies = [{ ...HARBOR, role: "member" }, NORTH, LARK];
        return { status: 200, body: { ...MEMBERS[0], role: "member" } };
      },
    });
    show("/c/harbor/settings");

    fireEvent.change(await screen.findByRole("combobox", { name: "Role of Ana Tran" }), {
      target: { value: "member" },
    });

    expect(await screen.findByRole("heading", { name: "Projects" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Company settings" })).not.toBeInTheDocument();
  });

  it("never shows one company's members under another company", async () => {
    fakeApi({
      ...SETTINGS,
      "GET /api/orgs": { status: 200, body: [HARBOR, { ...NORTH, role: "owner" }] },
      "GET /api/orgs/north/members": "hang",
      "GET /api/orgs/north/invites": "hang",
    });
    show("/c/harbor/settings");
    await screen.findByRole("table", { name: "Members" });

    fireEvent.click(screen.getByRole("link", { name: "go to north settings" }));

    expect(await screen.findByText(/Northwind Labs · you manage/)).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Members" })).not.toBeInTheDocument();
  });

  it("says the last owner must stay", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true); // demoting yourself asks first
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
    let people = MEMBERS;
    fakeApi({
      ...SETTINGS,
      "GET /api/orgs/harbor/members": () => ({ status: 200, body: people }),
      "DELETE /api/orgs/harbor/members/2": () => {
        people = [MEMBERS[0]!];
        return { status: 204 };
      },
    });
    show("/c/harbor/settings");

    fireEvent.click(await screen.findByRole("button", { name: "Remove Bo Le" }));

    await waitFor(() => expect(screen.queryByText("bo@gmail.com")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: /Members/ })).toHaveTextContent("(1)");
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
    let pending = INVITES;
    fakeApi({
      ...SETTINGS,
      "GET /api/orgs/harbor/invites": () => ({ status: 200, body: pending }),
      "DELETE /api/orgs/harbor/invites/7": () => {
        pending = [];
        return { status: 204 };
      },
    });
    show("/c/harbor/settings");

    fireEvent.click(await screen.findByRole("button", { name: "Revoke cy@gmail.com" }));

    expect(await screen.findByText("No pending invites.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Pending invites/ })).toHaveTextContent("(0)");
  });

  it("shows a member that only owners manage the company, under the heading, with Retry", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /api/orgs/north/members": { status: 403, body: error("FORBIDDEN") },
      "GET /api/orgs/north/invites": { status: 403, body: error("FORBIDDEN") },
    });

    show("/c/north/settings");

    expect(await screen.findByRole("alert")).toHaveTextContent("You do not have access to this.");
    expect(screen.getByRole("heading", { name: "Company settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("sends a person whose session ended to sign in", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /api/orgs/harbor/members": { status: 401, body: error("UNAUTHENTICATED") },
      "GET /api/orgs/harbor/invites": { status: 401, body: error("UNAUTHENTICATED") },
    });

    show("/c/harbor/settings");

    expect(await screen.findByText("Sign in page")).toBeInTheDocument();
  });
});
