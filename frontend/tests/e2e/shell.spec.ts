import { expect, test } from "@playwright/test";

import {
  NEUTRAL_ROUTE_MESSAGE,
  neutralRoutes,
} from "../../src/shared/config/neutral-routes";

test("renders technical route index with preserved routes @qa-final", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Índice técnico" })).toBeVisible();
  await expect(page.getByText(NEUTRAL_ROUTE_MESSAGE)).toBeVisible();

  for (const route of neutralRoutes) {
    const link = page.getByRole("link", { name: route.title });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", route.href);
  }
});

for (const route of neutralRoutes) {
  test(`renders neutral contract for ${route.href} @qa-final`, async ({ page }) => {
    await page.goto(route.href);

    await expect(page.getByRole("heading", { name: route.title })).toBeVisible();
    await expect(page.getByText(NEUTRAL_ROUTE_MESSAGE)).toBeVisible();
  });
}
