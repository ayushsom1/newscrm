import { expect, test } from "@playwright/test";
import { login } from "./_helpers";

test("login lands on the dashboard with KPI cards", async ({ page }) => {
  await login(page);

  // KPI cards from /dashboard/kpis
  await expect(page.getByText("Active advertisers")).toBeVisible();
  await expect(page.getByText("Active subscribers")).toBeVisible();
  await expect(page.getByText("Open complaints")).toBeVisible();

  // Exception queue header
  await expect(page.getByText(/exception queue/i)).toBeVisible();
});

test("bad credentials show an inline error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("admin@example.com");
  await page.getByLabel(/password/i).fill("wrong");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/invalid credentials/i)).toBeVisible();
});

test("unauthenticated visit to /advertisers redirects to /login", async ({ page }) => {
  await page.goto("/advertisers");
  await expect(page).toHaveURL(/\/login$/);
});
