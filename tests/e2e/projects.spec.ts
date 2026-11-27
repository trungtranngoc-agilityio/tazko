import { expect, test } from "@playwright/test";
import { companyOwner, signIn, unique } from "./accounts";

// Projects through the browser: Manage projects, a project's boards, members and
// invites, its settings, and what a new person invited to one project sees.

test("an owner creates a project, invites a new email, and that person sees only it", async ({
  page,
  browser,
}) => {
  const { slug, ownerPage, context } = await companyOwner(browser, page);
  const newcomer = `${unique("new")}@gmail.com`;

  // Manage projects: a project with the owner as its first owner opens on its boards
  await ownerPage.getByRole("link", { name: "Manage projects" }).first().click();
  await ownerPage.getByRole("button", { name: "New project" }).click();
  const dialog = ownerPage.getByRole("dialog", { name: "New project" });
  await dialog.getByLabel("Project name").fill("Website relaunch");
  await dialog.getByRole("button", { name: "Create project" }).click();
  await expect(ownerPage).toHaveURL(new RegExp(`/c/${slug}/p/\\d+/boards$`));
  await expect(
    ownerPage.getByRole("heading", { name: /Website relaunch/ }),
  ).toBeVisible();
  await ownerPage.getByRole("link", { name: /Members/ }).click();

  // invite someone new as a member
  await ownerPage.getByPlaceholder("name@example.com").fill(newcomer);
  await ownerPage.getByRole("button", { name: "Invite" }).click();
  await expect(
    ownerPage.getByRole("table", { name: "Pending invites" }),
  ).toContainText(newcomer);

  // the newcomer signs in and sees exactly that project, as a member
  const other = await browser.newContext();
  const newPage = await other.newPage();
  await signIn(newPage, newcomer, "Nia New");
  await newPage.goto(`/c/${slug}`);
  const card = newPage.getByRole("link", { name: /Website relaunch/ });
  await expect(card).toBeVisible();
  await expect(card).toContainText("member");
  await expect(newPage.getByRole("link", { name: "Manage projects" })).toHaveCount(0);
  await other.close();

  // the invite is used: the owner sees a member and no pending invite
  await ownerPage.reload();
  await expect(ownerPage.getByText("Nia New")).toBeVisible();
  await expect(ownerPage.getByText("No pending invites.")).toBeVisible();
  await context.close();
});

test("project settings keep their changes, and an observer only reads", async ({
  page,
  browser,
}) => {
  const { slug, ownerPage, context } = await companyOwner(browser, page);
  const watcher = `${unique("obs")}@gmail.com`;
  await ownerPage.goto(`/c/${slug}/manage`);
  await ownerPage.getByRole("button", { name: "New project" }).click();
  const dialog = ownerPage.getByRole("dialog", { name: "New project" });
  await dialog.getByLabel("Project name").fill("Mobile app");
  await dialog.getByRole("button", { name: "Create project" }).click();
  await expect(ownerPage).toHaveURL(/\/boards$/);

  // boards: a new board, starred, stays starred after a reload and shows on Your projects
  await ownerPage.getByRole("button", { name: "Create new board" }).click();
  const boardDialog = ownerPage.getByRole("dialog", { name: "Create board" });
  await boardDialog.getByLabel("Board title").fill("Sprint 1");
  await boardDialog.getByRole("button", { name: "Create board" }).click();
  const tile = ownerPage.getByRole("article", { name: "Sprint 1" });
  await expect(tile).toContainText("0 lists · 0 cards");
  await tile.getByRole("button", { name: "Star board" }).click();
  await expect(ownerPage.getByRole("region", { name: "Starred" })).toBeVisible();
  await ownerPage.reload();
  await expect(
    ownerPage
      .getByRole("region", { name: "Starred" })
      .getByRole("button", { name: "Star board" }),
  ).toHaveAttribute("aria-pressed", "true");
  await ownerPage.goto(`/c/${slug}`);
  await expect(
    ownerPage
      .getByRole("region", { name: "Starred boards" })
      .getByRole("article", { name: "Sprint 1" }),
  ).toBeVisible();
  await ownerPage.getByRole("link", { name: /Mobile app/ }).click();

  // settings: a switch and the description stay after a reload
  await ownerPage.getByRole("link", { name: "Settings", exact: true }).click();
  await ownerPage.getByRole("switch", { name: "Members can invite people" }).click();
  await ownerPage.getByLabel("Description").fill("Native app releases.");
  await ownerPage.getByRole("button", { name: "Save changes" }).click();
  await expect(ownerPage.getByText("Saved")).toBeVisible();
  await ownerPage.reload();
  await expect(
    ownerPage.getByRole("switch", { name: "Members can invite people" }),
  ).toHaveAttribute("aria-checked", "true");
  await expect(ownerPage.getByLabel("Description")).toHaveValue("Native app releases.");

  // an observer joins through an invite and can only read
  await ownerPage.getByRole("link", { name: /Members/ }).click();
  await ownerPage.getByPlaceholder("name@example.com").fill(watcher);
  await ownerPage.getByRole("combobox", { name: "Role", exact: true }).selectOption("observer");
  await ownerPage.getByRole("button", { name: "Invite" }).click();
  await expect(
    ownerPage.getByRole("table", { name: "Pending invites" }),
  ).toContainText(watcher);

  const other = await browser.newContext();
  const watcherPage = await other.newPage();
  await signIn(watcherPage, watcher, "Oscar Observer");
  await watcherPage.goto(`/c/${slug}`);
  await watcherPage.getByRole("link", { name: /Mobile app/ }).click();
  await expect(watcherPage.getByRole("article", { name: "Sprint 1" })).toBeVisible();
  await expect(watcherPage.getByRole("button", { name: "Create new board" })).toHaveCount(0);
  await expect(
    watcherPage.getByText(/Only project owners can create boards in this project/),
  ).toBeVisible();
  await watcherPage.getByRole("link", { name: /Members/ }).click();
  await expect(
    watcherPage.getByText("Only project owners can invite people."),
  ).toBeVisible();
  await expect(watcherPage.getByRole("combobox")).toHaveCount(0);
  await expect(watcherPage.getByRole("button", { name: /Remove/ })).toHaveCount(0);
  await expect(watcherPage.getByRole("link", { name: "Settings", exact: true })).toHaveCount(0);
  await other.close();
  await context.close();
});
