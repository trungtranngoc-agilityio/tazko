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

type Routes = Record<string, Reply | ((body: unknown) => Reply | Promise<Reply>)>;

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

  it("a member adds a list", async () => {
    const calls = signedIn({
      [`POST ${B}/lists`]: (body) => ({
        status: 201,
        body: list(13, (body as { name: string }).name),
      }),
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Add another list" }));
    const input = screen.getByRole("textbox", { name: "List title" });
    fireEvent.change(input, { target: { value: "  Review " } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"))).toEqual([
        "To do",
        "Done",
        "Review",
      ]),
    );
    expect(writes(calls)).toEqual([
      expect.objectContaining({ method: "POST", path: `${B}/lists`, body: { name: "Review" } }),
    ]);
  });

  it("a member adds cards one after another", async () => {
    let next = 200;
    const calls = signedIn({
      [`POST ${B}/lists/11/cards`]: (body) => ({
        status: 201,
        body: card(next++, 11, (body as { title: string }).title),
      }),
    });
    show();

    fireEvent.click(
      await within(await findColumn("To do")).findByRole("button", { name: "Add a card" }),
    );
    for (const title of ["Ship it", "Tell everyone"]) {
      const box = within(column("To do")).getByRole("textbox", { name: "Card title" });
      fireEvent.change(box, { target: { value: title } });
      fireEvent.keyDown(box, { key: "Enter" });
      await within(column("To do")).findByRole("article", { name: title });
    }

    expect(
      within(column("To do"))
        .getAllByRole("article")
        .map((a) => a.textContent),
    ).toEqual(["Write the brief", "Pick a date", "Ship it", "Tell everyone"]);
    expect(within(column("To do")).getByRole("textbox", { name: "Card title" })).toHaveValue("");
    expect(writes(calls).map((c) => c.body)).toEqual([
      { title: "Ship it" },
      { title: "Tell everyone" },
    ]);
  });

  it("a blank title sends nothing", async () => {
    const calls = signedIn();
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Add another list" }));
    fireEvent.click(screen.getByRole("button", { name: "Add list" }));
    fireEvent.click(within(column("To do")).getByRole("button", { name: "Add a card" }));
    const box = within(column("To do")).getByRole("textbox", { name: "Card title" });
    fireEvent.change(box, { target: { value: "   " } });
    fireEvent.click(within(column("To do")).getByRole("button", { name: "Add card" }));

    await new Promise((r) => setTimeout(r, 20));
    expect(writes(calls)).toEqual([]);
  });

  it("a refused add says why", async () => {
    signedIn({ [`POST ${B}/lists`]: { status: 409, body: apiError("TOO_MANY_LISTS") } });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Add another list" }));
    const input = screen.getByRole("textbox", { name: "List title" });
    fireEvent.change(input, { target: { value: "One more" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This board has 200 open lists. Archive some first.",
    );
    expect(screen.getAllByRole("region")).toHaveLength(2);
  });

  it("a refused card or rename says why and changes nothing", async () => {
    signedIn({
      [`POST ${B}/lists/12/cards`]: { status: 409, body: apiError("LIST_ARCHIVED") },
      [`PATCH ${B}/lists/11`]: { status: 409, body: apiError("BOARD_CLOSED") },
    });
    show();

    fireEvent.click(
      await within(await findColumn("Done")).findByRole("button", { name: "Add a card" }),
    );
    const box = within(column("Done")).getByRole("textbox", { name: "Card title" });
    fireEvent.change(box, { target: { value: "Late card" } });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This list is archived. Restore it first.",
    );
    expect(box).toHaveValue("Late card");
    expect(within(column("Done")).queryByRole("article")).toBeNull();

    const todo = within(column("To do")).getByRole("heading", { name: "To do" });
    fireEvent.click(within(todo).getByRole("button"));
    const input = screen.getByRole("textbox", { name: "List name" });
    fireEvent.change(input, { target: { value: "Later" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "This board is closed. Reopen it to make changes.",
      ),
    );
    expect(column("To do")).toBeVisible();
  });

  it("enter while an input method is composing sends nothing", async () => {
    const calls = signedIn();
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Add another list" }));
    const input = screen.getByRole("textbox", { name: "List title" });
    fireEvent.change(input, { target: { value: "Vie" } });
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    const heading = screen.getByRole("heading", { level: 1 });
    fireEvent.click(within(heading).getByRole("button"));
    const name = screen.getByRole("textbox", { name: "Board name" });
    fireEvent.change(name, { target: { value: "Kế" } });
    fireEvent.keyDown(name, { key: "Enter", isComposing: true });

    await new Promise((r) => setTimeout(r, 20));
    expect(writes(calls)).toEqual([]);
    expect(screen.getByRole("textbox", { name: "Board name" })).toHaveValue("Kế");
  });

  it("a member renames the board", async () => {
    const calls = signedIn({
      [`PATCH ${B}`]: (body) => ({ status: 200, body: board(body as Record<string, unknown>) }),
    });
    show();

    const heading = await screen.findByRole("heading", { level: 1 });
    fireEvent.click(within(heading).getByRole("button"));
    const input = screen.getByRole("textbox", { name: "Board name" });
    fireEvent.change(input, { target: { value: "Launch week" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(await screen.findByRole("heading", { level: 1, name: "Launch week" })).toBeVisible();
    expect(writes(calls)).toEqual([
      expect.objectContaining({ method: "PATCH", path: B, body: { name: "Launch week" } }),
    ]);
  });

  it("a member renames a list", async () => {
    const calls = signedIn({
      [`PATCH ${B}/lists/12`]: (body) => ({
        status: 200,
        body: list(12, (body as { name: string }).name),
      }),
    });
    show();

    const heading = within(await findColumn("Done")).getByRole("heading", { name: "Done" });
    fireEvent.click(within(heading).getByRole("button"));
    const input = screen.getByRole("textbox", { name: "List name" });
    fireEvent.change(input, { target: { value: "Shipped" } });
    fireEvent.blur(input);

    expect(await screen.findByRole("region", { name: "Shipped" })).toBeVisible();
    expect(writes(calls)).toEqual([
      expect.objectContaining({
        method: "PATCH",
        path: `${B}/lists/12`,
        body: { name: "Shipped" },
      }),
    ]);
  });

  it("escape or the same name sends nothing", async () => {
    const calls = signedIn();
    show();

    const heading = await screen.findByRole("heading", { level: 1 });
    fireEvent.click(within(heading).getByRole("button"));
    const input = screen.getByRole("textbox", { name: "Board name" });
    fireEvent.change(input, { target: { value: "Something else" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.getByRole("heading", { level: 1, name: "Launch plan" })).toBeVisible();

    const todo = within(column("To do")).getByRole("heading", { name: "To do" });
    fireEvent.click(within(todo).getByRole("button"));
    const listName = screen.getByRole("textbox", { name: "List name" });
    fireEvent.change(listName, { target: { value: " To do " } });
    fireEvent.keyDown(listName, { key: "Enter" });

    await new Promise((r) => setTimeout(r, 20));
    expect(writes(calls)).toEqual([]);
    expect(column("To do")).toBeVisible();
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

    expect(await screen.findByRole("button", { name: "Add another list" })).toBeVisible();
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

const member = (id: number, name: string, role: string) => ({
  user_id: id,
  name,
  email: `user${id}@harbor.vn`,
  avatar_url: null,
  role,
  account: "active",
  last_seen_at: null,
});
const MEMBERS = [
  member(1, "Ana Tran", "owner"),
  member(2, "Bao Le", "member"),
  member(3, "Chi Vo", "observer"),
];
const asOwner = { [`GET ${P}`]: { status: 200, body: project({ role: "owner" }) } };

describe("board actions", () => {
  it("a member archives a list and undoes it", async () => {
    const calls = signedIn({
      [`PATCH ${B}/lists/11`]: (body) => ({
        status: 200,
        body: (body as { archived: boolean }).archived
          ? { ...LISTS[0], archived_at: "2026-11-27T10:00:00.000Z" }
          : LISTS[0],
      }),
    });
    show();

    fireEvent.click(
      within(await findColumn("To do")).getByRole("button", { name: "List actions" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Archive this list" }));

    await screen.findByText("List archived");
    expect(screen.queryByRole("region", { name: "To do" })).toBeNull();
    fireEvent.click(within(screen.getByRole("status")).getByRole("button", { name: "Undo" }));

    await waitFor(() =>
      expect(screen.getAllByRole("region").map((r) => r.getAttribute("aria-label"))).toEqual([
        "To do",
        "Done",
      ]),
    );
    expect(within(column("To do")).getAllByRole("article")).toHaveLength(2);
    expect(screen.queryByText("List archived")).toBeNull();
    expect(writes(calls).map((c) => [c.method, c.path, c.body])).toEqual([
      ["PATCH", `${B}/lists/11`, { archived: true }],
      ["PATCH", `${B}/lists/11`, { archived: false }],
    ]);
  });

  it("a refused undo says why and keeps the note", async () => {
    signedIn({
      [`PATCH ${B}/lists/11`]: (body) =>
        (body as { archived: boolean }).archived
          ? { status: 200, body: { ...LISTS[0], archived_at: "2026-11-27T10:00:00.000Z" } }
          : { status: 409, body: apiError("TOO_MANY_LISTS") },
    });
    show();

    fireEvent.click(
      within(await findColumn("To do")).getByRole("button", { name: "List actions" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Archive this list" }));
    await screen.findByText("List archived");
    fireEvent.click(within(screen.getByRole("status")).getByRole("button", { name: "Undo" }));

    expect(await screen.findByRole("alert")).toBeVisible();
    expect(screen.getByText("List archived")).toBeVisible();
    expect(screen.queryByRole("region", { name: "To do" })).toBeNull();
  });

  it("a refused archive says why and keeps the list", async () => {
    signedIn({ [`PATCH ${B}/lists/11`]: { status: 403, body: apiError("FORBIDDEN") } });
    show();

    fireEvent.click(
      within(await findColumn("To do")).getByRole("button", { name: "List actions" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Archive this list" }));

    expect(await screen.findByRole("alert")).toBeVisible();
    expect(column("To do")).toBeVisible();
    expect(screen.queryByText("List archived")).toBeNull();
  });

  it("the list menu closes with escape", async () => {
    signedIn();
    show();

    fireEvent.click(
      within(await findColumn("To do")).getByRole("button", { name: "List actions" }),
    );
    fireEvent.keyDown(screen.getByRole("button", { name: "Archive this list" }), {
      key: "Escape",
    });

    expect(screen.queryByRole("button", { name: "Archive this list" })).toBeNull();
  });

  it("anyone who opens the board stars and unstars it", async () => {
    const calls = signedIn({
      [`GET ${P}`]: { status: 200, body: project({ role: "observer" }) },
      [`PUT ${B}/star`]: { status: 204 },
      [`DELETE ${B}/star`]: { status: 204 },
    });
    show();

    const star = await screen.findByRole("button", { name: "Star board" });
    expect(star).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(star);
    await waitFor(() => expect(star).toHaveAttribute("aria-pressed", "true"));
    fireEvent.click(star);
    await waitFor(() => expect(star).toHaveAttribute("aria-pressed", "false"));

    expect(writes(calls).map((c) => [c.method, c.path])).toEqual([
      ["PUT", `${B}/star`],
      ["DELETE", `${B}/star`],
    ]);
  });

  it("a star that answers late keeps an access change made meanwhile", async () => {
    let answerStar: (reply: { status: number }) => void = () => {};
    signedIn({
      ...asOwner,
      [`GET ${P}/members`]: { status: 200, body: MEMBERS },
      [`PUT ${B}/star`]: () => new Promise<Reply>((resolve) => (answerStar = resolve)),
      [`PUT ${B}/access`]: { status: 200, body: board({ restricted: true, access: [] }) },
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Star board" }));
    fireEvent.click(screen.getByRole("button", { name: "Whole project" }));
    const dialog = screen.getByRole("dialog", { name: "Board access" });
    fireEvent.click(await within(dialog).findByRole("switch", { name: "Restrict this board" }));
    await screen.findByRole("button", { name: "Restricted" });
    answerStar({ status: 204 });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Star board" })).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
    expect(screen.getByRole("button", { name: "Restricted" })).toBeVisible();
  });

  it("a project owner on a closed board has no board menu and no access switch", async () => {
    signedIn({
      ...asOwner,
      [`GET ${B}`]: { status: 200, body: board({ archived_at: "2026-11-20T10:00:00.000Z" }) },
    });
    show();

    expect(await screen.findByRole("button", { name: "Reopen board" })).toBeVisible();
    expectNoChangeControls();
    fireEvent.click(screen.getByRole("button", { name: "Whole project" }));
    const dialog = screen.getByRole("dialog", { name: "Board access" });
    expect(within(dialog).getByText("Visible to the whole project.")).toBeVisible();
    expect(within(dialog).queryByRole("switch")).toBeNull();
  });

  it("a member closes the board from the board menu", async () => {
    const calls = signedIn({
      [`PATCH ${B}`]: { status: 200, body: board({ archived_at: "2026-11-27T10:00:00.000Z" }) },
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Board menu" }));
    const menu = screen.getByRole("complementary", { name: "Board menu" });
    expect(within(menu).queryByRole("button", { name: "Board access" })).toBeNull();
    fireEvent.click(within(menu).getByRole("button", { name: "Close board" }));

    expect(
      await screen.findByText("This board is closed. Reopen it to make changes."),
    ).toBeVisible();
    expect(screen.queryByRole("complementary", { name: "Board menu" })).toBeNull();
    expectNoChangeControls();
    expect(writes(calls)).toEqual([
      expect.objectContaining({ method: "PATCH", path: B, body: { archived: true } }),
    ]);
  });

  it("the access chip tells a member who sees the board", async () => {
    const calls = signedIn({ [`GET ${B}`]: { status: 200, body: board({ restricted: true }) } });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Restricted" }));

    const dialog = screen.getByRole("dialog", { name: "Board access" });
    expect(within(dialog).getByText("Restricted to chosen members.")).toBeVisible();
    expect(within(dialog).queryByRole("switch")).toBeNull();
    expect(calls.some((c) => c.path === `${P}/members`)).toBe(false);
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Board access" })).toBeNull();
  });

  it("a project owner restricts the board to chosen members", async () => {
    const calls = signedIn({
      ...asOwner,
      [`GET ${P}/members`]: { status: 200, body: MEMBERS },
      [`PUT ${B}/access`]: (body) => {
        const { restricted, people } = body as { restricted: boolean; people: number[] };
        return { status: 200, body: board({ restricted, access: people }) };
      },
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Whole project" }));
    const dialog = screen.getByRole("dialog", { name: "Board access" });
    fireEvent.click(await within(dialog).findByRole("switch", { name: "Restrict this board" }));

    const bao = await within(dialog).findByRole("checkbox", { name: /Bao Le/ });
    const ana = within(dialog).getByRole("checkbox", { name: /Ana Tran/ });
    expect(ana).toBeChecked();
    expect(ana).toBeDisabled();
    expect(bao).not.toBeChecked();
    fireEvent.click(bao);

    await waitFor(() => expect(bao).toBeChecked());
    expect(screen.getByRole("button", { name: "Restricted" })).toBeVisible();
    expect(writes(calls).map((c) => c.body)).toEqual([
      { restricted: true, people: [] },
      { restricted: true, people: [2] },
    ]);
  });

  it("a project owner opens the board to the whole project again", async () => {
    const calls = signedIn({
      ...asOwner,
      [`GET ${B}`]: { status: 200, body: board({ restricted: true, access: [2] }) },
      [`GET ${P}/members`]: { status: 200, body: MEMBERS },
      [`PUT ${B}/access`]: { status: 200, body: board() },
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Board menu" }));
    fireEvent.click(screen.getByRole("button", { name: "Board access" }));
    const dialog = screen.getByRole("dialog", { name: "Board access" });
    expect(await within(dialog).findByRole("checkbox", { name: /Bao Le/ })).toBeChecked();
    fireEvent.click(within(dialog).getByRole("switch", { name: "Restrict this board" }));

    await waitFor(() => expect(within(dialog).queryByRole("checkbox")).toBeNull());
    expect(screen.getByRole("button", { name: "Whole project" })).toBeVisible();
    expect(writes(calls).map((c) => c.body)).toEqual([{ restricted: false, people: [] }]);
  });

  it("escape closes board access after a change, wherever the focus went", async () => {
    signedIn({
      ...asOwner,
      [`GET ${P}/members`]: { status: 200, body: MEMBERS },
      [`PUT ${B}/access`]: { status: 200, body: board({ restricted: true, access: [] }) },
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Whole project" }));
    const dialog = screen.getByRole("dialog", { name: "Board access" });
    fireEvent.click(await within(dialog).findByRole("switch", { name: "Restrict this board" }));
    await screen.findByRole("button", { name: "Restricted" });
    fireEvent.keyDown(document.body, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: "Board access" })).toBeNull();
  });

  it("a refused access change says why and changes nothing", async () => {
    signedIn({
      ...asOwner,
      [`GET ${P}/members`]: { status: 200, body: MEMBERS },
      [`PUT ${B}/access`]: { status: 422, body: apiError("NOT_A_PROJECT_MEMBER") },
    });
    show();

    fireEvent.click(await screen.findByRole("button", { name: "Whole project" }));
    const dialog = screen.getByRole("dialog", { name: "Board access" });
    const restrict = await within(dialog).findByRole("switch", { name: "Restrict this board" });
    fireEvent.click(restrict);

    expect(await within(dialog).findByRole("alert")).toBeVisible();
    expect(restrict).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("button", { name: "Whole project" })).toBeVisible();
  });
});

async function findColumn(name: string) {
  return screen.findByRole("region", { name });
}

function expectNoChangeControls() {
  expect(screen.queryByRole("button", { name: "Add another list" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Add a card" })).toBeNull();
  const heading = screen.getByRole("heading", { level: 1 });
  expect(within(heading).queryByRole("button")).toBeNull();
  expect(within(column("To do")).queryByRole("button", { name: /To do/ })).toBeNull();
  expect(screen.queryByRole("button", { name: "List actions" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Board menu" })).toBeNull();
}
