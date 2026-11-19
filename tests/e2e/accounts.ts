import { expect, type Page } from "@playwright/test";

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
