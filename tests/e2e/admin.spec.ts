import { expect, test } from "@playwright/test";
import { SUPER_ADMIN, signIn, unique } from "./accounts";

// The whole round trip through the browser: Google sign-in (stand-in),
// session cookie, web app, console API.

test("the super admin made with `tazko admin` signs in and reaches the console", async ({
  page,
}) => {
  await signIn(page, SUPER_ADMIN, "Root Admin");

  await page.goto("/admin");

  await expect(page.getByRole("heading", { name: "Companies" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0); // not "Only super admins…"
  await expect(
    page.getByRole("navigation", { name: "Admin console" }),
  ).toBeVisible();
  // the name comes from the Google profile at the first sign-in
  await expect(page.getByRole("complementary")).toContainText("Root Admin");
});

test("a company made in the console lets its first owner in", async ({
  page,
  browser,
}) => {
  const slug = unique("e2e");
  const owner = `owner@${slug}.test`;
  await signIn(page, SUPER_ADMIN, "Root Admin");
  await page.goto("/admin");

  // the super admin creates the company and invites its first owner
  await page.getByRole("button", { name: "New company" }).click();
  const dialog = page.getByRole("dialog", { name: "New company" });
  await dialog.getByLabel("Company name").fill(`Studio ${slug}`);
  await dialog.getByLabel(/Short name/).fill(slug);
  await dialog.getByLabel("First owner email").fill(owner);
  await dialog.getByRole("button", { name: "Create company" }).click();
  await expect(page).toHaveURL(`/admin/companies/${slug}`);
  await expect(
    page.getByRole("table", { name: "Pending invites" }),
  ).toContainText(owner);

  // the owner signs in in another browser and lands in the company
  const other = await browser.newContext();
  const ownerPage = await other.newPage();
  await signIn(ownerPage, owner, "Olive Owner");
  await expect(
    ownerPage.getByRole("heading", { name: "Projects" }),
  ).toBeVisible();
  await expect(
    ownerPage.getByText(`Studio ${slug} · you see the projects`),
  ).toBeVisible();
  await ownerPage.getByRole("link", { name: "Company settings" }).click();
  await expect(
    ownerPage.getByRole("combobox", { name: "Role of Olive Owner" }),
  ).toHaveValue("owner");
  await other.close();

  // and the console no longer lists the invite as pending
  await page.reload();
  await expect(page.getByText("No pending invites.")).toBeVisible();
});

test("an account nobody invited is refused and told which account it was", async ({
  page,
}) => {
  const stranger = `${unique("stranger")}@gmail.com`;

  await signIn(page, stranger);

  await expect(page).toHaveURL(/\/signin\/refused/);
  await expect(
    page.getByRole("heading", { name: "This account is not invited" }),
  ).toBeVisible();
  await expect(page.getByText(stranger)).toBeVisible();
});

test("a company suspended in the console turns its owner away at sign-in", async ({
  page,
  browser,
}) => {
  const slug = unique("e2e");
  const owner = `owner@${slug}.test`;
  await signIn(page, SUPER_ADMIN, "Root Admin");
  await page.goto("/admin");
  await page.getByRole("button", { name: "New company" }).click();
  const dialog = page.getByRole("dialog", { name: "New company" });
  await dialog.getByLabel("Company name").fill(`Studio ${slug}`);
  await dialog.getByLabel(/Short name/).fill(slug);
  await dialog.getByLabel("First owner email").fill(owner);
  await dialog.getByRole("button", { name: "Create company" }).click();
  const other = await browser.newContext();
  const ownerPage = await other.newPage();
  await signIn(ownerPage, owner, "Olive Owner");
  await expect(
    ownerPage.getByRole("heading", { name: "Projects" }),
  ).toBeVisible();

  // the super admin suspends the company
  await page.getByRole("button", { name: "Suspend" }).click();
  await expect(page.getByRole("button", { name: "Resume" })).toBeVisible();

  // the owner's next sign-in is refused and says why
  await signIn(ownerPage, owner);
  await expect(ownerPage).toHaveURL(/\/signin\/refused/);
  await expect(
    ownerPage.getByRole("heading", { name: "Your company is suspended" }),
  ).toBeVisible();
  await other.close();
});
