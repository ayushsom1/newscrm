import { expect, test } from "@playwright/test";
import { login, nonce } from "./_helpers";

test("classified intake shows a live quote and locks price at booking", async ({
  page,
}) => {
  await login(page);
  await page.goto("/classifieds/new");

  const customer = `E2E Reader ${nonce()}`;
  await page.getByLabel(/customer name/i).fill(customer);
  await page.getByLabel(/^phone$/i).fill("+919" + Date.now().toString().slice(-9));
  await page
    .getByLabel(/ad text/i)
    .fill(
      "Two BHK flat available for rent near central park, contact owner directly.",
    );
  // Category select defaults to GENERAL — change to PROPERTY for a 1.30x multiplier
  await page.getByLabel(/category/i).selectOption("PROPERTY");
  await page.getByLabel(/duration/i).fill("7");

  // Live quote appears in the side panel. "Total" row + currency symbol.
  await expect(page.getByText(/^total$/i)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/^net$/i)).toBeVisible();

  // Book at quoted price
  await page.getByRole("button", { name: /book at quoted price/i }).click();

  // Lands on classifieds list — find the new row by customer name
  await expect(page).toHaveURL(/\/classifieds$/);
  await expect(page.getByText(customer)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("QUOTED").first()).toBeVisible();

  // Mark paid -> published. Both transitions are inline buttons on the row.
  const row = page.getByRole("row", { name: new RegExp(customer) });
  await row.getByRole("button", { name: /mark paid/i }).click();
  await expect(row.getByText("PAID")).toBeVisible({ timeout: 10_000 });
  await row.getByRole("button", { name: /^publish$/i }).click();
  await expect(row.getByText("PUBLISHED")).toBeVisible({ timeout: 10_000 });
});
