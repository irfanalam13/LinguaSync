import { test, expect } from "@playwright/test";

test("landing renders hero + CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Localize any video/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /Try the dashboard/i })).toBeVisible();
});

test("unauthenticated dashboard redirects to login", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});

test("login screen shows email + password fields", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByPlaceholder("Email")).toBeVisible();
  await expect(page.getByPlaceholder("Password")).toBeVisible();
});
