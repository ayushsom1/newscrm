import { expect, type Page } from "@playwright/test";

/**
 * Seeded admin user from backend/app/scripts/seed.py.
 * The DB is preserved across specs; tests use unique names where collisions
 * matter.
 */
export const ADMIN_EMAIL = "admin@example.com";
export const ADMIN_PASSWORD = "admin123";

export async function login(
  page: Page,
  email = ADMIN_EMAIL,
  password = ADMIN_PASSWORD,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  // Wait for the app shell to render.
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible({
    timeout: 15_000,
  });
}

/** Unique-ish suffix so repeat runs don't clash on names/phones. */
export function nonce(): string {
  return Math.random().toString(36).slice(2, 8);
}
