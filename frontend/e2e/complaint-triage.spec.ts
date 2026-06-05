import { expect, test } from "@playwright/test";
import { login, nonce } from "./_helpers";

test("billing dispute always escalates (engine guard, AI never called)", async ({
  page,
}) => {
  await login(page);
  await page.goto("/complaints/new");

  const customer = `E2E Bill ${nonce()}`;
  await page.getByLabel(/subscriber name/i).fill(customer);
  await page.getByLabel(/^phone$/i).fill("+91999" + Date.now().toString().slice(-8));
  await page.getByLabel(/area/i).fill("Patan");
  await page
    .getByLabel(/complaint text/i)
    .fill("You double charged my card this month. This is a billing dispute, please refund.");
  await page.getByRole("button", { name: /save complaint/i }).click();

  // Detail view loads. Triage hasn't run yet.
  await expect(page.getByRole("heading", { name: customer })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/triage hasn't been run/i)).toBeVisible();

  await page.getByRole("button", { name: /run triage/i }).click();

  // Sensitive guard fires BEFORE AI -> source=ENGINE, ESCALATED.
  await expect(page.getByText(/ESCALATED/).first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/ENGINE/).first()).toBeVisible();
  // Awaiting human action banner shown.
  await expect(page.getByText(/awaiting human action/i)).toBeVisible();
});

test("routine pause request can auto-resolve", async ({ page }) => {
  await login(page);
  await page.goto("/complaints/new");

  const customer = `E2E Pause ${nonce()}`;
  await page.getByLabel(/subscriber name/i).fill(customer);
  await page.getByLabel(/^phone$/i).fill("+91888" + Date.now().toString().slice(-8));
  await page.getByLabel(/area/i).fill("Patan");
  await page
    .getByLabel(/complaint text/i)
    .fill("Please pause my subscription for the next two weeks while I am traveling.");
  await page.getByRole("button", { name: /save complaint/i }).click();

  await expect(page.getByRole("heading", { name: customer })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: /run triage/i }).click();

  // Either AI or ENGINE auto-resolves; the badge is AUTO.
  await expect(page.getByText(/AUTO/).first()).toBeVisible({ timeout: 30_000 });
});
