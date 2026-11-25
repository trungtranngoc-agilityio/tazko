import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyLayout } from "@/app/layouts/CompanyLayout";
import { CompanyHomePage } from "@/pages/company/CompanyHomePage";
import { fakeApi, type Reply } from "@/test/fakeApi";

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
});
