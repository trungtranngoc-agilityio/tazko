import { expect, test } from "@playwright/test";
import { companyOwner, signIn, unique } from "./accounts";

// A board through the browser: open it from its tile, add a list and a card,
// rename the list, archive it and take it back, star the board, reload; then an
// observer reads it without any way to change it.

test("a board keeps its lists and cards, and an observer only reads it", async ({
  page,
  browser,
}) => {
  const { slug, ownerPage, context } = await companyOwner(browser, page);
  const watcher = `${unique("obs")}@gmail.com`;
  await ownerPage.goto(`/c/${slug}/manage`);
  await ownerPage.getByRole("button", { name: "New project" }).click();
  const dialog = ownerPage.getByRole("dialog", { name: "New project" });
  await dialog.getByLabel("Project name").fill("Launch");
  await dialog.getByRole("button", { name: "Create project" }).click();
  await expect(ownerPage).toHaveURL(/\/boards$/);
  await ownerPage.getByRole("button", { name: "Create new board" }).click();
  const boardDialog = ownerPage.getByRole("dialog", { name: "Create board" });
  await boardDialog.getByLabel("Board title").fill("Sprint 1");
  await boardDialog.getByRole("button", { name: "Create board" }).click();

  // the tile opens the board
  await ownerPage.getByRole("link", { name: "Sprint 1" }).click();
  await expect(ownerPage).toHaveURL(new RegExp(`/c/${slug}/p/\\d+/b/\\d+$`));
  await expect(ownerPage.getByRole("heading", { level: 1, name: "Sprint 1" })).toBeVisible();
  const boardUrl = ownerPage.url();

  // a list, a card in it, and the list renamed
  await ownerPage.getByRole("button", { name: "Add another list" }).click();
  await ownerPage.getByRole("textbox", { name: "List title" }).fill("To do");
  await ownerPage.getByRole("textbox", { name: "List title" }).press("Enter");
  const todo = ownerPage.getByRole("region", { name: "To do" });
  await todo.getByRole("button", { name: "Add a card" }).click();
  await todo.getByRole("textbox", { name: "Card title" }).fill("Write the brief");
  await todo.getByRole("textbox", { name: "Card title" }).press("Enter");
  await expect(todo.getByRole("article", { name: "Write the brief" })).toBeVisible();
  await todo.getByRole("heading", { name: "To do" }).getByRole("button").click();
  await ownerPage.getByRole("textbox", { name: "List name" }).fill("Doing");
  await ownerPage.getByRole("textbox", { name: "List name" }).press("Enter");
  await expect(ownerPage.getByRole("region", { name: "Doing" })).toBeVisible();

  // archived and taken back with Undo, and the board starred
  await ownerPage
    .getByRole("region", { name: "Doing" })
    .getByRole("button", { name: "List actions" })
    .click();
  await ownerPage.getByRole("button", { name: "Archive this list" }).click();
  await expect(ownerPage.getByRole("region", { name: "Doing" })).toHaveCount(0);
  await ownerPage.getByRole("status").getByRole("button", { name: "Undo" }).click();
  await expect(ownerPage.getByRole("region", { name: "Doing" })).toBeVisible();
  await ownerPage.getByRole("button", { name: "Star board" }).click();
  await expect(ownerPage.getByRole("button", { name: "Star board" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  // all of it survives a reload
  await ownerPage.reload();
  const doing = ownerPage.getByRole("region", { name: "Doing" });
  await expect(doing.getByRole("article", { name: "Write the brief" })).toBeVisible();
  await expect(ownerPage.getByRole("button", { name: "Star board" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  // an observer reads the board with no way to change it
  await ownerPage.goto(boardUrl.replace(/\/b\/\d+$/, "/members"));
  await ownerPage.getByPlaceholder("name@example.com").fill(watcher);
  await ownerPage.getByRole("combobox", { name: "Role", exact: true }).selectOption("observer");
  await ownerPage.getByRole("button", { name: "Invite" }).click();
  await expect(ownerPage.getByRole("table", { name: "Pending invites" })).toContainText(watcher);

  const other = await browser.newContext();
  const watcherPage = await other.newPage();
  await signIn(watcherPage, watcher, "Oscar Observer");
  await watcherPage.goto(new URL(boardUrl).pathname);
  await expect(
    watcherPage
      .getByRole("region", { name: "Doing" })
      .getByRole("article", { name: "Write the brief" }),
  ).toBeVisible();
  await expect(watcherPage.getByText(/You are an observer on this project/)).toBeVisible();
  await expect(watcherPage.getByRole("button", { name: "Add a card" })).toHaveCount(0);
  await expect(watcherPage.getByRole("button", { name: "Add another list" })).toHaveCount(0);
  await expect(watcherPage.getByRole("button", { name: "List actions" })).toHaveCount(0);
  await other.close();
  await context.close();
});
