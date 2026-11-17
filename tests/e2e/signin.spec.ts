import { expect, test } from "@playwright/test";

// The full Google round trip is covered by backend/tests/integration/test_auth.py
// with a fake provider; here the screens and the redirect for signed-out visitors.

test("a signed-out visitor is sent to sign in", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/signin$/);
  await expect(
    page.getByRole("heading", { name: "Sign in to Tazko" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Continue with Google" }),
  ).toHaveAttribute("href", /\/auth\/google\/start$/);
});

test("Continue with Google starts on the API", async ({ request }) => {
  const res = await request.get("/auth/google/start", { maxRedirects: 0 });

  expect(res.status()).toBe(302);
  expect(res.headers()["location"]).toContain("code_challenge_method=S256");
});

test("the refusal screen explains itself without a refused account", async ({
  page,
}) => {
  await page.goto("/signin/refused");

  await expect(
    page.getByRole("heading", { name: "This account is not invited" }),
  ).toBeVisible();
  await expect(
    page.getByText("This Google account is not on the list for Tazko."),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Try another Google account" }),
  ).toBeVisible();
});
