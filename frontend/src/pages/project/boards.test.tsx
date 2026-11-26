import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyLayout } from "@/app/layouts/CompanyLayout";
import { ProjectBoardsPage } from "@/pages/project/ProjectBoardsPage";
import { apiError, fakeApi, type Reply } from "@/test/fakeApi";

const ANA = {
  id: 1,
  email: "ana@harbor.vn",
  name: "Ana Tran",
  avatar_url: null,
  is_super_admin: false,
};
const HARBOR = { slug: "harbor", name: "Harbor Studio", role: "member", status: "active" };
const P = "/api/orgs/harbor/projects";
const B = `${P}/5/boards`;

const project = (over: Record<string, unknown> = {}) => ({
  id: 5,
  name: "Website relaunch",
  description: "",
  color: "c0",
  default_background: "sea",
  members_can_create_boards: true,
  members_can_invite: false,
  aging_enabled: true,
  aging_days: 7,
  created_at: "2026-11-01T10:00:00.000Z",
  archived_at: null,
  role: "member",
  ...over,
});
const board = (id: number, name: string, over: Record<string, unknown> = {}) => ({
  id,
  project_id: 5,
  name,
  background: "dusk",
  restricted: false,
  starred: false,
  access: null,
  lists: 0,
  cards: 0,
  created_at: "2026-11-02T10:00:00.000Z",
  archived_at: null,
  ...over,
});

type Routes = Record<string, Reply | ((body: unknown) => Reply)>;

function signedIn(routes: Routes = {}) {
  return fakeApi({
    "GET /api/me": { status: 200, body: ANA },
    "GET /api/orgs": { status: 200, body: [HARBOR] },
    [`GET ${P}/5/members`]: { status: 200, body: [] },
    ...routes,
  });
}

function show(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/c/:slug" element={<CompanyLayout />}>
          <Route path="p/:projectId/boards" element={<ProjectBoardsPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

const tile = (name: string) => screen.getByRole("article", { name });

afterEach(() => vi.unstubAllGlobals());

describe("project boards", () => {
  it("shows starred boards apart, with lists, cards and a restricted mark", async () => {
    signedIn({
      [`GET ${P}/5`]: { status: 200, body: project() },
      [`GET ${B}`]: {
        status: 200,
        body: [
          board(1, "Launch plan", { starred: true, lists: 3, cards: 12 }),
          board(2, "Secret", { restricted: true, lists: 1, cards: 1 }),
        ],
      },
    });
    show("/c/harbor/p/5/boards");

    const starred = await screen.findByRole("region", { name: "Starred" });
    expect(within(starred).getByText("Launch plan")).toBeInTheDocument();
    const all = screen.getByRole("region", { name: "All boards" });
    expect(
      within(all)
        .getAllByRole("article")
        .map((a) => a.getAttribute("aria-label")),
    ).toEqual(["Launch plan", "Secret"]);
    expect(within(tile("Secret")).getByText("Restricted · 1 list · 1 card")).toBeInTheDocument();
    expect(within(all).getByText("3 lists · 12 cards")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Boards" })).toHaveAttribute("aria-current", "page");
  });

  it("creates a board with a name and the project's background unless another is picked", async () => {
    const calls = signedIn({
      [`GET ${P}/5`]: { status: 200, body: project() },
      [`GET ${B}`]: { status: 200, body: [board(1, "Launch plan"), board(2, "Zebra")] },
      [`POST ${B}`]: (body) => ({
        status: 201,
        body: board(7, (body as { name: string }).name, { background: "rose" }),
      }),
    });
    show("/c/harbor/p/5/boards");

    fireEvent.click(await screen.findByRole("button", { name: "Create new board" }));
    const dialog = screen.getByRole("dialog", { name: "Create board" });
    expect(within(dialog).getByRole("button", { name: "Background sea" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.change(within(dialog).getByLabelText("Board title"), {
      target: { value: " Sprint 15 " },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Background rose" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Create board" }));

    expect(await screen.findByRole("article", { name: "Sprint 15" })).toBeInTheDocument();
    const all = screen.getByRole("region", { name: "All boards" });
    expect(
      within(all)
        .getAllByRole("article")
        .map((a) => a.getAttribute("aria-label")),
    ).toEqual(["Launch plan", "Sprint 15", "Zebra"]);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      name: "Sprint 15",
      background: "rose",
    });
  });

  it("tells an observer, and a member when the project says so, who creates boards", async () => {
    signedIn({
      [`GET ${P}/5`]: { status: 200, body: project({ role: "observer" }) },
      [`GET ${B}`]: { status: 200, body: [board(1, "Launch plan")] },
    });
    show("/c/harbor/p/5/boards");

    expect(
      await screen.findByText(/Only project owners can create boards in this project/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create new board" })).toBeNull();
  });

  it("offers no create tile to a member when members may not create boards", async () => {
    signedIn({
      [`GET ${P}/5`]: { status: 200, body: project({ members_can_create_boards: false }) },
      [`GET ${B}`]: { status: 200, body: [] },
    });
    show("/c/harbor/p/5/boards");

    expect(await screen.findByText(/Only project owners can create boards/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create new board" })).toBeNull();
  });

  it("stars and unstars a board", async () => {
    const calls = signedIn({
      [`GET ${P}/5`]: { status: 200, body: project() },
      [`GET ${B}`]: { status: 200, body: [board(1, "Launch plan")] },
      [`PUT ${B}/1/star`]: { status: 204 },
      [`DELETE ${B}/1/star`]: { status: 204 },
    });
    show("/c/harbor/p/5/boards");

    const star = within(await screen.findByRole("article", { name: "Launch plan" })).getByRole(
      "button",
      { name: "Star board" },
    );
    fireEvent.click(star);
    expect(await screen.findByRole("region", { name: "Starred" })).toBeInTheDocument();
    const again = within(screen.getByRole("region", { name: "Starred" })).getByRole("button", {
      name: "Star board",
    });
    expect(again).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(again);

    await waitFor(() => expect(screen.queryByRole("region", { name: "Starred" })).toBeNull());
    expect(calls.filter((c) => c.path === `${B}/1/star`).map((c) => c.method)).toEqual([
      "PUT",
      "DELETE",
    ]);
  });

  it("lists closed boards on request and reopens one", async () => {
    const calls = signedIn({
      [`GET ${P}/5`]: { status: 200, body: project() },
      [`GET ${B}`]: {
        status: 200,
        body: [
          board(1, "Open one"),
          board(2, "Old sprint", { archived_at: "2026-11-03T00:00:00Z" }),
        ],
      },
      [`PATCH ${B}/2`]: { status: 200, body: board(2, "Old sprint") },
    });
    show("/c/harbor/p/5/boards");

    await screen.findByRole("article", { name: "Open one" });
    expect(screen.queryByRole("article", { name: "Old sprint" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Show closed boards (1)" }));
    const closed = screen.getByRole("region", { name: "Closed boards" });
    fireEvent.click(within(closed).getByRole("button", { name: "Reopen Old sprint" }));

    expect(await screen.findByRole("article", { name: "Old sprint" })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ archived: false });
    expect(screen.queryByRole("button", { name: /closed boards/ })).toBeNull();
  });

  it("shows an observer the closed boards without Reopen", async () => {
    signedIn({
      [`GET ${P}/5`]: { status: 200, body: project({ role: "observer" }) },
      [`GET ${B}`]: {
        status: 200,
        body: [board(2, "Old sprint", { archived_at: "2026-11-03T00:00:00Z" })],
      },
    });
    show("/c/harbor/p/5/boards");

    fireEvent.click(await screen.findByRole("button", { name: "Show closed boards (1)" }));
    expect(
      within(screen.getByRole("region", { name: "Closed boards" })).queryByRole("button"),
    ).toBeNull();
  });

  it("tells a company owner outside the project to add themselves", async () => {
    signedIn({
      [`GET ${P}/5`]: { status: 200, body: project({ role: null }) },
      [`GET ${B}`]: { status: 403, body: apiError("NOT_IN_PROJECT") },
    });
    show("/c/harbor/p/5/boards");

    expect(await screen.findByRole("alert")).toHaveTextContent(/add yourself/i);
  });
});
