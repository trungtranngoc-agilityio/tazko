import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompanyLayout } from "@/app/layouts/CompanyLayout";
import { BoardPage } from "@/pages/board/BoardPage";
import { apiError, fakeApi, type Call, type Reply } from "@/test/fakeApi";

const ANA = {
  id: 1,
  email: "ana@harbor.vn",
  name: "Ana Tran",
  avatar_url: null,
  is_super_admin: false,
};
const HARBOR = { slug: "harbor", name: "Harbor Studio", role: "member", status: "active" };
const P = "/api/orgs/harbor/projects/5";
const B = `${P}/boards/7`;

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
const board = (over: Record<string, unknown> = {}) => ({
  id: 7,
  project_id: 5,
  name: "Launch plan",
  background: "sea",
  restricted: false,
  starred: false,
  access: null,
  lists: 2,
  cards: 2,
  created_at: "2026-11-02T10:00:00.000Z",
  archived_at: null,
  ...over,
});
const card = (id: number, listId: number, title: string) => ({
  id,
  list_id: listId,
  title,
  rank: `a${id}`,
  due_at: null,
  done_at: null,
  cover_color: null,
  created_at: "2026-11-03T10:00:00.000Z",
  updated_at: "2026-11-03T10:00:00.000Z",
  archived_at: null,
});
const list = (id: number, name: string, cards: ReturnType<typeof card>[] = []) => ({
  id,
  board_id: 7,
  name,
  rank: `a${id}`,
  created_at: "2026-11-02T10:00:00.000Z",
  archived_at: null,
  cards,
});
const LISTS = [
  list(11, "To do", [card(101, 11, "Write the brief"), card(102, 11, "Pick a date")]),
  list(12, "Done"),
];

type Routes = Record<string, Reply | ((body: unknown) => Reply)>;

function signedIn(routes: Routes = {}): Call[] {
  return fakeApi({
    "GET /api/me": { status: 200, body: ANA },
    "GET /api/orgs": { status: 200, body: [HARBOR] },
    [`GET ${P}`]: { status: 200, body: project() },
    [`GET ${B}`]: { status: 200, body: board() },
    [`GET ${B}/lists`]: { status: 200, body: LISTS },
    ...routes,
  });
}

function show() {
  render(
    <MemoryRouter initialEntries={["/c/harbor/p/5/b/7"]}>
      <Routes>
        <Route path="/c/:slug" element={<CompanyLayout />}>
          <Route path="p/:projectId/b/:boardId" element={<BoardPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

const writes = (calls: Call[]) => calls.filter((c) => c.method !== "GET");
const column = (name: string) => screen.getByRole("region", { name });

afterEach(() => vi.unstubAllGlobals());

describe("board screen", () => {
  it("shows the lists in order with their cards", async () => {
    signedIn();
    show();

    expect(await screen.findByRole("heading", { level: 1, name: "Launch plan" })).toBeVisible();
    const lists = screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"));
    expect(lists).toEqual(["To do", "Done"]);
    const todo = column("To do");
    expect(
      within(todo)
        .getAllByRole("article")
        .map((a) => a.textContent),
    ).toEqual(["Write the brief", "Pick a date"]);
    expect(within(todo).getByText("2")).toBeVisible();
    expect(within(column("Done")).getByText("No cards yet")).toBeVisible();
    expect(screen.getByRole("link", { name: "Website relaunch" })).toHaveAttribute(
      "href",
      "/c/harbor/p/5/boards",
    );
  });

  it("a list collapses and opens again", async () => {
    signedIn();
    show();

    fireEvent.click(
      await within(await findColumn("To do")).findByRole("button", { name: "Collapse list" }),
    );
    expect(within(column("To do")).queryByRole("article")).toBeNull();
    expect(screen.getByRole("button", { name: "Expand list To do" })).toHaveTextContent(
      "To do · 2",
    );
    fireEvent.click(screen.getByRole("button", { name: "Expand list To do" }));
    expect(within(column("To do")).getAllByRole("article")).toHaveLength(2);
  });

  it("an observer only reads", async () => {
    signedIn({ [`GET ${P}`]: { status: 200, body: project({ role: "observer" }) } });
    show();

    expect(
      await screen.findByText(
        "You are an observer on this project. You can read everything but not make changes.",
      ),
    ).toBeVisible();
    expect(within(column("To do")).getAllByRole("article")).toHaveLength(2);
    expectNoChangeControls();
  });

  it("a closed board is read-only with Reopen", async () => {
    const calls = signedIn({
      [`GET ${B}`]: { status: 200, body: board({ archived_at: "2026-11-20T10:00:00.000Z" }) },
      [`PATCH ${B}`]: { status: 200, body: board() },
    });
    show();

    expect(
      await screen.findByText("This board is closed. Reopen it to make changes."),
    ).toBeVisible();
    expectNoChangeControls();
    fireEvent.click(screen.getByRole("button", { name: "Reopen board" }));

    await waitFor(() =>
      expect(screen.queryByText("This board is closed. Reopen it to make changes.")).toBeNull(),
    );
    expect(writes(calls)).toEqual([
      expect.objectContaining({ method: "PATCH", path: B, body: { archived: false } }),
    ]);
  });

  it("an observer on a closed board is not told to reopen it", async () => {
    signedIn({
      [`GET ${P}`]: { status: 200, body: project({ role: "observer" }) },
      [`GET ${B}`]: { status: 200, body: board({ archived_at: "2026-11-20T10:00:00.000Z" }) },
    });
    show();

    expect(await screen.findByText(/You are an observer on this project/)).toBeVisible();
    expect(screen.queryByText(/Reopen it/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Reopen board" })).toBeNull();
  });

  it("an archived project's board is read-only", async () => {
    signedIn({
      [`GET ${P}`]: {
        status: 200,
        body: project({ role: "owner", archived_at: "2026-11-20T10:00:00.000Z" }),
      },
    });
    show();

    expect(
      await screen.findByText("This project is archived, so its boards are read-only."),
    ).toBeVisible();
    expectNoChangeControls();
    expect(screen.queryByRole("button", { name: "Reopen board" })).toBeNull();
  });

  it("a failed load says so and tries again", async () => {
    let fail = true;
    signedIn({
      [`GET ${B}/lists`]: () =>
        fail ? { status: 500, body: apiError("INTERNAL") } : { status: 200, body: LISTS },
    });
    show();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong on our side. Try again.",
    );
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("region", { name: "To do" })).toBeVisible();
  });

  it("a refused board says why with a way back and no retry", async () => {
    signedIn({ [`GET ${B}`]: { status: 403, body: apiError("NOT_IN_PROJECT") } });
    show();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Add yourself to the project to open its boards.",
    );
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    expect(screen.getByRole("link", { name: "Back to the project" })).toHaveAttribute(
      "href",
      "/c/harbor/p/5/boards",
    );
  });

  it("a missing board says so", async () => {
    signedIn({ [`GET ${B}`]: { status: 404, body: apiError("NOT_FOUND") } });
    show();

    expect(await screen.findByRole("heading", { name: "Board not found" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the project" })).toHaveAttribute(
      "href",
      "/c/harbor/p/5/boards",
    );
  });
});

async function findColumn(name: string) {
  return screen.findByRole("region", { name });
}

function expectNoChangeControls() {
  const heading = screen.getByRole("heading", { level: 1 });
  expect(within(heading).queryByRole("button")).toBeNull();
}
