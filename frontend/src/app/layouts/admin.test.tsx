import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation, useRoutes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiError, fakeApi } from "@/test/fakeApi";
import { routes } from "../router";

// Names, emails and audit targets come from Google profiles that anyone can
// set (M1.md, security review): they must show as text, never as markup.
const HOSTILE = "<img src=x onerror=alert(1)>";

const ROOT = {
  id: 1,
  email: "root@tazko.dev",
  name: "Root Admin",
  avatar_url: null,
  is_super_admin: true,
};
const HARBOR = {
  slug: "harbor",
  name: "Harbor Studio",
  status: "active",
  members: 2,
  storage_bytes: 512 * 1024 * 1024,
  storage_limit_bytes: 2 * 1024 * 1024 * 1024,
  last_activity_at: null,
};
const LARK = { ...HARBOR, slug: "lark", name: HOSTILE, status: "suspended", members: 0 };
const MEMBERS = [
  {
    user_id: 2,
    name: "Ana Tran",
    email: "ana@harbor.vn",
    avatar_url: null,
    account: "workspace",
    role: "owner",
    last_seen_at: null,
  },
];
const INVITE = {
  id: 7,
  email: "cy@gmail.com",
  role: "member",
  account: "personal",
  invited_by: "Ana Tran",
  created_at: "2026-11-05T10:00:00.000Z",
  expires_at: "2026-11-19T10:00:00.000Z",
};
const PERSON = {
  id: 2,
  name: "Ana Tran",
  email: "ana@harbor.vn",
  avatar_url: null,
  account: "workspace",
  companies: [{ slug: "harbor", name: "Harbor Studio", role: "owner" }],
  last_seen_at: null,
  is_super_admin: false,
  active: true,
};

const SIGNED_IN = { "GET /api/me": { status: 200, body: ROOT } };

let here = "";

function App() {
  here = useLocation().pathname;
  return useRoutes(routes);
}

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("console shell", () => {
  it("links every console page and the way back to the app", async () => {
    fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [] } });

    show("/admin");

    const nav = await screen.findByRole("navigation", { name: "Admin console" });
    expect(
      within(nav)
        .getAllByRole("link")
        .map((link) => [link.textContent, link.getAttribute("href")]),
    ).toEqual([
      ["Back to app", "/"],
      ["Companies", "/admin"],
      ["People", "/admin/people"],
      ["Invites", "/admin/invites"],
      ["Audit log", "/admin/audit"],
      ["Server", "/admin/server"],
    ]);
  });

  it("tells a person who is not a super admin, without calling the console API", async () => {
    const calls = fakeApi({
      "GET /api/me": { status: 200, body: { ...ROOT, is_super_admin: false } },
    });

    show("/admin");

    expect(await screen.findByRole("alert")).toHaveTextContent("Only super admins");
    expect(calls.some((c) => c.path.startsWith("/admin/api"))).toBe(false);
  });
});

describe("companies", () => {
  it("lists companies with status, members and storage, names as text", async () => {
    fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [HARBOR, LARK] } });

    show("/admin");

    const table = await screen.findByRole("table", { name: "Companies" });
    const harbor = within(table).getByRole("row", { name: /Harbor Studio/ });
    expect(harbor).toHaveTextContent("Active");
    expect(harbor).toHaveTextContent("512 MB / 2 GB");
    expect(within(table).getByText(HOSTILE)).toBeInTheDocument();
    expect(within(table).getByText("Suspended")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });

  it("opens a company from its row", async () => {
    fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [HARBOR] } });
    show("/admin");

    fireEvent.click(await screen.findByRole("link", { name: /Harbor Studio/ }));

    await waitFor(() => expect(here).toBe("/admin/companies/harbor"));
  });

  it("creates a company, invites its first owner and opens it", async () => {
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/companies": { status: 200, body: [] },
      "POST /admin/api/companies": { status: 201, body: { ...HARBOR, slug: "acme", name: "Acme" } },
      "POST /admin/api/companies/acme/invites": {
        status: 201,
        body: { ...INVITE, email: "boss@acme.vn", role: "owner" },
      },
    });
    show("/admin");

    fireEvent.click(await screen.findByRole("button", { name: "New company" }));
    const dialog = screen.getByRole("dialog", { name: "New company" });
    fireEvent.change(within(dialog).getByLabelText("Company name"), {
      target: { value: "Acme Studio" },
    });
    expect(within(dialog).getByLabelText(/Short name/)).toHaveValue("acme-studio");
    fireEvent.change(within(dialog).getByLabelText(/Short name/), { target: { value: "acme" } });
    fireEvent.change(within(dialog).getByLabelText("First owner email"), {
      target: { value: "boss@acme.vn" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create company" }));

    await waitFor(() => expect(here).toBe("/admin/companies/acme"));
    const posts = calls.filter((c) => c.method === "POST").map((c) => [c.path, c.body]);
    expect(posts).toEqual([
      ["/admin/api/companies", { slug: "acme", name: "Acme Studio" }],
      ["/admin/api/companies/acme/invites", { email: "boss@acme.vn", role: "owner" }],
    ]);
  });

  it("explains a taken short name and keeps the dialog open", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/companies": { status: 200, body: [HARBOR] },
      "POST /admin/api/companies": { status: 409, body: apiError("SLUG_TAKEN") },
    });
    show("/admin");

    fireEvent.click(await screen.findByRole("button", { name: "New company" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Company name"), {
      target: { value: "Harbor" },
    });
    fireEvent.change(within(dialog).getByLabelText("First owner email"), {
      target: { value: "x@harbor.vn" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create company" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "That address is already used by another company.",
    );
  });

  it("closes the dialog with Escape without creating anything", async () => {
    const calls = fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [] } });
    show("/admin");

    fireEvent.click(await screen.findByRole("button", { name: "New company" }));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });
});

describe("company detail", () => {
  const DETAIL = {
    ...SIGNED_IN,
    "GET /admin/api/companies/harbor": { status: 200, body: HARBOR },
    "GET /admin/api/companies/harbor/members": { status: 200, body: MEMBERS },
    "GET /admin/api/companies/harbor/invites": { status: 200, body: [INVITE] },
  };

  it("shows the company with its members and invites from the console API", async () => {
    fakeApi(DETAIL);

    show("/admin/companies/harbor");

    expect(await screen.findByRole("heading", { name: "Harbor Studio" })).toBeInTheDocument();
    expect(screen.getByText(/\/ Harbor Studio/)).toBeInTheDocument(); // breadcrumb
    const members = await screen.findByRole("table", { name: "Members" });
    expect(within(members).getByText("ana@harbor.vn")).toBeInTheDocument();
    const invites = screen.getByRole("table", { name: "Pending invites" });
    expect(within(invites).getByText("cy@gmail.com")).toBeInTheDocument();
  });

  it("refuses to remove the last owner and says why", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const calls = fakeApi({
      ...DETAIL,
      "DELETE /admin/api/companies/harbor/members/2": { status: 409, body: apiError("LAST_OWNER") },
    });
    show("/admin/companies/harbor");

    fireEvent.click(await screen.findByRole("button", { name: "Remove Ana Tran" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A company needs at least one owner.",
    );
    expect(calls.some((c) => c.method === "DELETE")).toBe(true);
  });

  it("invites through the console API", async () => {
    const calls = fakeApi({
      ...DETAIL,
      "POST /admin/api/companies/harbor/invites": {
        status: 201,
        body: { ...INVITE, id: 8, email: "di@harbor.vn" },
      },
    });
    show("/admin/companies/harbor");

    fireEvent.change(await screen.findByRole("textbox", { name: "Email" }), {
      target: { value: "di@harbor.vn" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    expect(await screen.findByText(/Invited di@harbor.vn/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.path).toBe(
      "/admin/api/companies/harbor/invites",
    );
  });

  it("says when the company does not exist", async () => {
    fakeApi(SIGNED_IN);

    show("/admin/companies/gone");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This no longer exists, or you do not have access to it.",
    );
  });
});

describe("people", () => {
  it("lists people with their companies, names as text", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/people": {
        status: 200,
        body: {
          items: [PERSON, { ...PERSON, id: 3, name: HOSTILE, email: "x@gmail.com" }],
          next: null,
        },
      },
    });

    show("/admin/people");

    const table = await screen.findByRole("table", { name: "People" });
    const ana = within(table).getByRole("row", { name: /Ana Tran/ });
    expect(ana).toHaveTextContent("Harbor Studio");
    expect(ana).toHaveTextContent("Workspace");
    expect(within(table).getByText(HOSTILE)).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });

  it("searches by name or email on the server", async () => {
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/people": (_body, query) => ({
        status: 200,
        body: { items: query.get("q") === "zed" ? [] : [PERSON], next: null },
      }),
    });
    show("/admin/people");
    await screen.findByText("ana@harbor.vn");

    fireEvent.change(screen.getByRole("searchbox", { name: "Search people" }), {
      target: { value: "zed" },
    });

    expect(await screen.findByText("No one matches.")).toBeInTheDocument();
    expect(calls.at(-1)?.query.get("q")).toBe("zed");
  });

  it("loads the next page with the cursor", async () => {
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/people": (_body, query) =>
        query.get("after") === "2"
          ? { status: 200, body: { items: [{ ...PERSON, id: 3, name: "Bo Le" }], next: null } }
          : { status: 200, body: { items: [PERSON], next: 2 } },
    });
    show("/admin/people");

    fireEvent.click(await screen.findByRole("button", { name: "Show more" }));

    expect(await screen.findByText("Bo Le")).toBeInTheDocument();
    expect(screen.getByText("Ana Tran")).toBeInTheDocument();
    expect(calls.at(-1)?.query.get("after")).toBe("2");
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
  });

  it("turns super admin on and shows what the server kept", async () => {
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/people": { status: 200, body: { items: [PERSON], next: null } },
      "PATCH /admin/api/people/2": { status: 200, body: { ...PERSON, is_super_admin: true } },
    });
    show("/admin/people");

    const toggle = await screen.findByRole("switch", { name: "Super admin for Ana Tran" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    fireEvent.click(toggle);

    await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ is_super_admin: true });
  });

  it("explains that you cannot change your own access", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/people": {
        status: 200,
        body: {
          items: [{ ...PERSON, id: 1, name: "Root Admin", is_super_admin: true }],
          next: null,
        },
      },
      "PATCH /admin/api/people/1": { status: 409, body: apiError("SELF_CHANGE") },
    });
    show("/admin/people");

    fireEvent.click(await screen.findByRole("switch", { name: "Active for Root Admin" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("You cannot change your own access");
    expect(screen.getByRole("switch", { name: "Active for Root Admin" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});

describe("invites", () => {
  it("lists every pending invite with its company and revokes one", async () => {
    let pending = [{ ...INVITE, company: { slug: "harbor", name: "Harbor Studio" } }];
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/invites": () => ({ status: 200, body: pending }),
      "DELETE /admin/api/invites/7": () => {
        pending = [];
        return { status: 204 };
      },
    });
    show("/admin/invites");

    const table = await screen.findByRole("table", { name: "Invites" });
    expect(within(table).getByRole("row", { name: /cy@gmail.com/ })).toHaveTextContent(
      "Harbor Studio",
    );
    fireEvent.click(within(table).getByRole("button", { name: "Revoke cy@gmail.com" }));

    expect(await screen.findByText("No pending invites")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/admin/api/invites/7")).toBe(
      true,
    );
  });
});

describe("audit log", () => {
  const REFUSED = {
    id: 9,
    at: "2026-11-18T08:00:00Z",
    action: "signin.refused",
    actor: null,
    company: null,
    target: HOSTILE,
    detail: null,
    ip: "203.0.113.5",
  };
  const CREATED = {
    ...REFUSED,
    id: 8,
    action: "company.created",
    actor: { id: 1, name: "Root Admin", email: "root@tazko.dev" },
    company: { slug: "harbor", name: "Harbor Studio" },
    target: "harbor",
  };

  it("writes each entry as a sentence, targets as text, refusals marked", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/audit": { status: 200, body: { items: [REFUSED, CREATED], next: null } },
    });

    show("/admin/audit");

    const log = await screen.findByRole("list", { name: "Audit log" });
    const [refused, created] = within(log).getAllByRole("listitem");
    expect(refused).toHaveTextContent(`Someone was refused sign-in ${HOSTILE}`);
    expect(refused).toHaveTextContent("refused");
    expect(created).toHaveTextContent("Root Admin created company harbor");
    expect(document.querySelector("img")).toBeNull();
  });

  it("filters by kind on the server", async () => {
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/audit": { status: 200, body: { items: [CREATED], next: null } },
    });
    show("/admin/audit");
    await screen.findByRole("list", { name: "Audit log" });

    fireEvent.change(screen.getByRole("combobox", { name: "Filter" }), {
      target: { value: "signin" },
    });

    await waitFor(() => expect(calls.at(-1)?.query.get("kind")).toBe("signin"));
  });

  it("loads older entries with the cursor", async () => {
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/audit": (_body, query) =>
        query.get("before") === "8"
          ? { status: 200, body: { items: [{ ...CREATED, id: 3, target: "older" }], next: null } }
          : { status: 200, body: { items: [CREATED], next: 8 } },
    });
    show("/admin/audit");

    fireEvent.click(await screen.findByRole("button", { name: "Show more" }));

    expect(await screen.findByText("older")).toBeInTheDocument();
    expect(calls.at(-1)?.query.get("before")).toBe("8");
  });
});

describe("server", () => {
  const SERVER = {
    ...SIGNED_IN,
    "GET /admin/api/server": {
      status: 200,
      body: {
        version: "0.1.0",
        public_url: "https://tazko-dev.example.com",
        uptime_seconds: 6 * 86400 + 4 * 3600 + 59,
        data_bytes: Math.round(2.5 * 1024 ** 3),
        last_backup: null,
        email: { enabled: false, host: null, port: null, sender: null },
      },
    },
    "GET /admin/api/workspace-domains": {
      status: 200,
      body: [{ domain: "harbor.vn", first_seen_at: "2026-11-01T00:00:00Z" }],
    },
  };

  it("shows version, uptime, data size, backup and email status", async () => {
    fakeApi(SERVER);

    show("/admin/server");

    expect(await screen.findByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText("https://tazko-dev.example.com")).toBeInTheDocument();
    expect(screen.getByText("6 days 4 h")).toBeInTheDocument();
    expect(screen.getByText("2.5 GB")).toBeInTheDocument();
    expect(screen.getByText("Not set up yet")).toBeInTheDocument();
    expect(screen.getByText("Not configured")).toBeInTheDocument();
  });

  it("forgets a Workspace domain after asking", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    let domains = [{ domain: "harbor.vn", first_seen_at: "2026-11-01T00:00:00Z" }];
    const calls = fakeApi({
      ...SERVER,
      "GET /admin/api/workspace-domains": () => ({ status: 200, body: domains }),
      "DELETE /admin/api/workspace-domains/harbor.vn": () => {
        domains = [];
        return { status: 204 };
      },
    });
    show("/admin/server");

    fireEvent.click(await screen.findByRole("button", { name: "Forget harbor.vn" }));

    expect(confirm).toHaveBeenCalled();
    expect(await screen.findByText("No Workspace domains recorded.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE")).toBe(true);
  });
});

describe("states the review asked for", () => {
  it("says the companies list is empty", async () => {
    fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [] } });

    show("/admin");

    expect(await screen.findByText("No companies yet")).toBeInTheDocument();
  });

  it("explains a failed load and loads again on Try again", async () => {
    let fail = true;
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/companies": () =>
        fail ? { status: 500, body: apiError("INTERNAL") } : { status: 200, body: [] },
    });
    show("/admin");

    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side.");
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("No companies yet")).toBeInTheDocument();
  });

  it("suggests a short name from a Vietnamese company name", async () => {
    fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [] } });
    show("/admin");

    fireEvent.click(await screen.findByRole("button", { name: "New company" }));
    fireEvent.change(screen.getByLabelText("Company name"), {
      target: { value: "Đà Nẵng Studio" },
    });

    expect(screen.getByLabelText(/Short name/)).toHaveValue("da-nang-studio");
  });

  it("asks for a name instead of sending only spaces", async () => {
    const calls = fakeApi({ ...SIGNED_IN, "GET /admin/api/companies": { status: 200, body: [] } });
    show("/admin");

    fireEvent.click(await screen.findByRole("button", { name: "New company" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Company name"), { target: { value: "   " } });
    fireEvent.change(within(dialog).getByLabelText(/Short name/), { target: { value: "x" } });
    fireEvent.change(within(dialog).getByLabelText("First owner email"), {
      target: { value: "a@b.vn" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create company" }));

    expect(within(dialog).getByRole("alert")).toHaveTextContent("Give the company a name.");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("opens the new company and says why its first owner was not invited", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/companies": { status: 200, body: [] },
      "POST /admin/api/companies": { status: 201, body: HARBOR },
      "POST /admin/api/companies/harbor/invites": {
        status: 409,
        body: apiError("ALREADY_MEMBER"),
      },
      "GET /admin/api/companies/harbor": { status: 200, body: HARBOR },
      "GET /admin/api/companies/harbor/members": { status: 200, body: MEMBERS },
      "GET /admin/api/companies/harbor/invites": { status: 200, body: [] },
    });
    show("/admin");

    fireEvent.click(await screen.findByRole("button", { name: "New company" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Company name"), {
      target: { value: "Harbor Studio" },
    });
    fireEvent.change(within(dialog).getByLabelText("First owner email"), {
      target: { value: "ana@harbor.vn" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create company" }));

    expect(await screen.findByRole("heading", { name: "Harbor Studio" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The company was created, but the first owner was not invited: This person is already a member",
    );
  });

  it("shows a suspended company read-only", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/companies/harbor": { status: 200, body: { ...HARBOR, status: "suspended" } },
      "GET /admin/api/companies/harbor/members": { status: 200, body: MEMBERS },
      "GET /admin/api/companies/harbor/invites": { status: 200, body: [INVITE] },
    });

    show("/admin/companies/harbor");

    await screen.findByRole("table", { name: "Members" });
    expect(screen.getByText(/This company is suspended/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Invite" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove Ana Tran" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revoke cy@gmail.com" })).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Role of Ana Tran" })).toBeDisabled();
  });

  it("keeps a Workspace domain when the super admin cancels", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const calls = fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/server": "hang",
      "GET /admin/api/workspace-domains": {
        status: 200,
        body: [{ domain: "harbor.vn", first_seen_at: "2026-11-01T00:00:00Z" }],
      },
    });
    show("/admin/server");

    fireEvent.click(await screen.findByRole("button", { name: "Forget harbor.vn" }));

    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    expect(screen.getByText("harbor.vn")).toBeInTheDocument();
  });

  it("keeps the list and says why Show more failed", async () => {
    fakeApi({
      ...SIGNED_IN,
      "GET /admin/api/people": (_body, query) =>
        query.get("after")
          ? { status: 429, body: apiError("RATE_LIMITED") }
          : { status: 200, body: { items: [PERSON], next: 2 } },
    });
    show("/admin/people");

    fireEvent.click(await screen.findByRole("button", { name: "Show more" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests.");
    expect(screen.getByText("Ana Tran")).toBeInTheDocument();
  });
});
