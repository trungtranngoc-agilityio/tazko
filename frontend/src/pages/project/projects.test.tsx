import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyLayout } from "@/app/layouts/CompanyLayout";
import { CompanyHomePage } from "@/pages/company/CompanyHomePage";
import { ManageProjectsPage } from "@/pages/company/ManageProjectsPage";
import { ProjectMembersPage } from "@/pages/project/ProjectMembersPage";
import { apiError, fakeApi, type Reply } from "@/test/fakeApi";

const ANA = {
  id: 1,
  email: "ana@harbor.vn",
  name: "Ana Tran",
  avatar_url: null,
  is_super_admin: false,
};
const HARBOR = { slug: "harbor", name: "Harbor Studio", role: "owner", status: "active" };
const P = "/api/orgs/harbor/projects";

const project = (over: Record<string, unknown> = {}) => ({
  id: 5,
  name: "Website relaunch",
  description: "Marketing site and blog.",
  color: "c0",
  default_background: "dusk",
  members_can_create_boards: true,
  members_can_invite: false,
  aging_enabled: true,
  aging_days: 7,
  created_at: "2026-11-01T10:00:00.000Z",
  archived_at: null,
  role: "owner",
  ...over,
});
const person = (user_id: number, name: string, role: string) => ({
  user_id,
  name,
  email: `${name.split(" ")[0]!.toLowerCase()}@harbor.vn`,
  avatar_url: null,
  role,
  account: "workspace",
  last_seen_at: null,
});
const PEOPLE = [person(1, "Ana Tran", "owner"), person(2, "Bo Le", "member")];
const INVITES = [
  {
    id: 9,
    email: "cy@gmail.com",
    role: "owner",
    account: "personal",
    invited_by: "Ana Tran",
    created_at: "2026-11-05T10:00:00.000Z",
    expires_at: "2026-11-19T10:00:00.000Z",
  },
];

function signedIn(
  company = HARBOR,
  routes: Record<string, Reply | ((body: unknown) => Reply)> = {},
) {
  return fakeApi({
    "GET /api/me": { status: 200, body: ANA },
    "GET /api/orgs": { status: 200, body: [company] },
    ...routes,
  });
}

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/c/:slug" element={<CompanyLayout />}>
          <Route index element={<CompanyHomePage />} />
          <Route path="manage" element={<ManageProjectsPage />} />
          <Route path="p/:projectId/members" element={<ProjectMembersPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("your projects", () => {
  it("shows each project with its people, the boards you can open and your role", async () => {
    signedIn(HARBOR, {
      [`GET ${P}`]: {
        status: 200,
        body: [{ ...project(), members: 2, people: PEOPLE, boards: 3 }],
      },
    });

    show("/c/harbor");

    const card = await screen.findByRole("link", { name: /Website relaunch/ });
    expect(card).toHaveAttribute("href", "/c/harbor/p/5");
    expect(card).toHaveTextContent("3 boards");
    expect(card).toHaveTextContent("owner");
    expect(within(card).getByLabelText("2 people")).toBeInTheDocument();
  });

  it("offers Manage projects to company owners only", async () => {
    signedIn({ ...HARBOR, role: "member" }, { [`GET ${P}`]: { status: 200, body: [] } });

    show("/c/harbor");

    expect(await screen.findByText("You are not in a project yet")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Manage projects" })).not.toBeInTheDocument();
  });

  it("shows company owners the Manage projects button and link", async () => {
    signedIn(HARBOR, { [`GET ${P}`]: { status: 200, body: [] } });

    show("/c/harbor");

    await screen.findByText("You are not in a project yet");
    expect(screen.getAllByRole("link", { name: "Manage projects" })).toHaveLength(2);
  });
});

describe("manage projects", () => {
  const ROWS = [
    {
      id: 5,
      name: "Website relaunch",
      color: "c0",
      archived_at: null,
      owners: [],
      members: 0,
      boards: 2,
    },
  ];
  const manage = (more: Record<string, Reply | ((body: unknown) => Reply)> = {}) =>
    signedIn(HARBOR, {
      [`GET ${P}`]: { status: 200, body: ROWS },
      "GET /api/orgs/harbor/members": {
        status: 200,
        body: PEOPLE.map((p) => ({ ...p, role: "owner" })),
      },
      ...more,
    });

  it("asks before deleting, and deletes nothing when the answer is no", async () => {
    const calls = manage();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    show("/c/harbor/manage");

    fireEvent.click(await screen.findByRole("button", { name: "Delete Website relaunch" }));

    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("trash for 30 days"));
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
  });

  it("archives with one click and says when a project has no owner", async () => {
    const calls = manage({
      [`PATCH ${P}/5`]: { status: 200, body: project({ archived_at: "x" }) },
    });
    show("/c/harbor/manage");

    expect(await screen.findByText("No owner")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Archive Website relaunch" }));

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ archived: true }),
    );
  });

  it("makes someone already in the project its owner by changing their role", async () => {
    const calls = manage({
      [`POST ${P}/5/members`]: { status: 409, body: apiError("ALREADY_PROJECT_MEMBER") },
      [`PATCH ${P}/5/members/2`]: { status: 200, body: person(2, "Bo Le", "owner") },
    });
    show("/c/harbor/manage");

    fireEvent.change(await screen.findByLabelText("Add an owner to Website relaunch"), {
      target: { value: "2" },
    });

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ role: "owner" }),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("tells a company member it is for owners, without calling the API", async () => {
    const calls = signedIn({ ...HARBOR, role: "member" });
    show("/c/harbor/manage");

    expect(
      await screen.findByText("Only owners of the company can manage projects."),
    ).toBeInTheDocument();
    expect(calls.some((c) => c.path === P)).toBe(false);
  });
});

describe("project members", () => {
  const MEMBER_CO = { ...HARBOR, role: "member" };
  const members = (
    p: ReturnType<typeof project>,
    more: Record<string, Reply | ((body: unknown) => Reply)> = {},
    company = HARBOR,
  ) =>
    signedIn(company, {
      [`GET ${P}/5`]: { status: 200, body: p },
      [`GET ${P}/5/members`]: { status: 200, body: PEOPLE },
      [`GET ${P}/5/invites`]: { status: 200, body: INVITES },
      ...more,
    });

  it("lets a project owner invite as member, observer or owner and change roles", async () => {
    members(project());
    show("/c/harbor/p/5/members");

    const role = await screen.findByRole("combobox", { name: "Role" });
    expect([...role.querySelectorAll("option")].map((o) => o.value)).toEqual([
      "member",
      "observer",
      "owner",
    ]);
    expect(screen.getByRole("combobox", { name: "Role of Bo Le" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revoke cy@gmail.com" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText("Ana Tran (you)")).toBeInTheDocument();
  });

  it("shows an observer the roles as text and why they cannot invite", async () => {
    members(project({ role: "observer", members_can_invite: true }), {}, MEMBER_CO);
    show("/c/harbor/p/5/members");

    expect(await screen.findByText(/Only project owners can invite people/)).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Remove/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Revoke/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Settings" })).not.toBeInTheDocument();
    // they may leave, and do not see when others last signed in
    expect(screen.getByRole("button", { name: "Leave" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Last active" })).not.toBeInTheDocument();
  });

  it("tells a member why they cannot invite when the project does not allow it", async () => {
    members(project({ role: "member", members_can_invite: false }), {}, MEMBER_CO);
    show("/c/harbor/p/5/members");

    expect(await screen.findByText(/Only project owners can invite people/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("name@example.com")).not.toBeInTheDocument();
  });

  it("lets a company owner who only observes the project invite owners", async () => {
    members(project({ role: "observer" }));
    show("/c/harbor/p/5/members");

    const role = await screen.findByRole("combobox", { name: "Role" });
    expect([...role.querySelectorAll("option")].map((o) => o.value)).toEqual(["owner"]);
    expect(screen.getByRole("button", { name: "Revoke cy@gmail.com" })).toBeInTheDocument();
  });

  it("changes a role, and says why when the server keeps the last owner", async () => {
    const calls = members(project(), {
      [`PATCH ${P}/5/members/2`]: { status: 200, body: person(2, "Bo Le", "observer") },
      [`PATCH ${P}/5/members/1`]: { status: 409, body: apiError("LAST_OWNER") },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    show("/c/harbor/p/5/members");

    fireEvent.change(await screen.findByRole("combobox", { name: "Role of Bo Le" }), {
      target: { value: "observer" },
    });
    await waitFor(() =>
      expect(calls.find((c) => c.path.endsWith("/members/2"))?.body).toEqual({ role: "observer" }),
    );
    fireEvent.change(screen.getByRole("combobox", { name: "Role of Ana Tran" }), {
      target: { value: "member" },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A project needs at least one owner.",
    );
  });

  it("asks before an owner gives up their own ownership", async () => {
    const calls = members(project());
    vi.spyOn(window, "confirm").mockReturnValue(false);
    show("/c/harbor/p/5/members");

    fireEvent.change(await screen.findByRole("combobox", { name: "Role of Ana Tran" }), {
      target: { value: "member" },
    });

    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("Stop being an owner"));
    expect(calls.some((c) => c.method === "PATCH")).toBe(false);
  });

  it("lets a member invite members and observers when the project allows it, and revoke only those", async () => {
    members(project({ role: "member", members_can_invite: true }), {}, MEMBER_CO);
    show("/c/harbor/p/5/members");

    const role = await screen.findByRole("combobox", { name: "Role" });
    expect([...role.querySelectorAll("option")].map((o) => o.value)).toEqual([
      "member",
      "observer",
    ]);
    expect(screen.queryByRole("button", { name: "Revoke cy@gmail.com" })).not.toBeInTheDocument();
  });

  it("invites and shows the new invite", async () => {
    let pending: unknown[] = [];
    const calls = members(project(), {
      [`GET ${P}/5/invites`]: () => ({ status: 200, body: pending }),
      [`POST ${P}/5/invites`]: (body) => {
        pending = [{ ...INVITES[0], email: "new@gmail.com", role: "member" }];
        return { status: 201, body: { ...INVITES[0], ...(body as object) } };
      },
    });
    show("/c/harbor/p/5/members");

    fireEvent.change(await screen.findByPlaceholderText("name@example.com"), {
      target: { value: " new@gmail.com " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    expect(await screen.findByRole("cell", { name: "new@gmail.com" })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      email: "new@gmail.com",
      role: "member",
    });
  });

  it("says why when the project is not found", async () => {
    signedIn(HARBOR);
    show("/c/harbor/p/5/members");

    expect(await screen.findByRole("alert")).toHaveTextContent("This no longer exists");
  });
});
