import { expect, test } from "@playwright/test";
import { login, nonce } from "./_helpers";

test("create advertiser, AI-draft proposal, approve, send", async ({ page }) => {
  await login(page);

  const name = `E2E Advertiser ${nonce()}`;

  // Create advertiser
  await page.goto("/advertisers");
  await page.getByRole("link", { name: /new advertiser/i }).click();
  await page.getByLabel(/^name$/i).fill(name);
  await page.getByLabel(/category/i).first().fill("Auto");
  await page.getByLabel(/contact email/i).fill("e2e@example.com");
  await page.getByLabel(/spend trend/i).fill("-15");
  await page.getByLabel(/proposal open rate/i).fill("40");
  await page.getByRole("button", { name: /^save$/i }).click();

  // Lands on detail page
  await expect(page.getByRole("heading", { name })).toBeVisible({ timeout: 15_000 });

  // AI draft (or engine fallback if no OPENROUTER_API_KEY)
  await page.getByRole("button", { name: /draft with ai/i }).click();

  // The new proposal card appears. Click it to expand.
  const card = page.getByText(/renewal|proposal/i).first();
  await expect(card).toBeVisible({ timeout: 30_000 });
  await card.click();

  // Approve. We accept the confirm() dialog for needs_human cases.
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: /^approve$/i }).first().click();

  // Status flips to APPROVED -> Send button shown.
  await expect(page.getByText(/^APPROVED$/).first()).toBeVisible({
    timeout: 15_000,
  });

  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: /^send$/i }).first().click();

  await expect(page.getByText(/^SENT$/).first()).toBeVisible({
    timeout: 15_000,
  });
});
