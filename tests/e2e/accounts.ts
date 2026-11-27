import { expect, type Browser, type Page } from "@playwright/test";

/** Made by `tazko admin --email` before the API starts (playwright.config.ts). */
export const SUPER_ADMIN = "root@e2e.test";

/** A value no other run or project has used, for slugs and addresses. */
export function unique(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

/** Continue with Google, choose `email` on the stand-in Google, and wait to be
 * back in the web app. */
export async function signIn(
  page: Page,
  email: string,
  name?: string,
): Promise<void> {
  await page.goto("/signin");
  await page.getByRole("link", { name: "Continue with Google" }).click();
  await expect(
    page.getByRole("heading", { name: "Choose an account" }),
  ).toBeVisible();
  await page.getByLabel("Email").fill(email);
  if (name) await page.getByLabel("Name").fill(name);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForURL(
    (url) => url.port === "5173" && !url.pathname.startsWith("/auth/"),
  );
}

/** A fresh company whose first owner is signed in on the returned page. */
export async function companyOwner(browser: Browser, page: Page) {
  const slug = unique("proj");
  const owner = `owner@${slug}.test`;
  await signIn(page, SUPER_ADMIN, "Root Admin");
  await page.goto("/admin");
  await page.getByRole("button", { name: "New company" }).click();
  const dialog = page.getByRole("dialog", { name: "New company" });
  await dialog.getByLabel("Company name").fill(`Studio ${slug}`);
  await dialog.getByLabel(/Short name/).fill(slug);
  await dialog.getByLabel("First owner email").fill(owner);
  await dialog.getByRole("button", { name: "Create company" }).click();
  await expect(page).toHaveURL(`/admin/companies/${slug}`);

  const context = await browser.newContext();
  const ownerPage = await context.newPage();
  await signIn(ownerPage, owner, "Olive Owner");
  return { slug, ownerPage, context };
}
