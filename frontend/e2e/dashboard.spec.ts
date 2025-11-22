import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test.use({ storageState: ".playwright/.auth/user.json" });

  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("should display dashboard with key metrics", async ({ page }) => {
    // Check main heading
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();

    // Check stat cards are present
    await expect(page.getByText(/agentes activos/i)).toBeVisible();
    await expect(page.getByText(/tokens usados/i)).toBeVisible();
    await expect(page.getByText(/conversaciones/i)).toBeVisible();
  });

  test("should display usage chart", async ({ page }) => {
    // Check for chart container
    await expect(page.getByTestId("usage-chart")).toBeVisible();
  });

  test("should display recent activity", async ({ page }) => {
    // Check for activity section
    await expect(page.getByText(/actividad reciente/i)).toBeVisible();
  });

  test("should navigate to agents page", async ({ page }) => {
    await page.getByRole("link", { name: /agentes/i }).click();
    await expect(page).toHaveURL(/\/agents/);
  });

  test("should navigate to documents page", async ({ page }) => {
    await page.getByRole("link", { name: /documentos/i }).click();
    await expect(page).toHaveURL(/\/documents/);
  });

  test("should navigate to chat page", async ({ page }) => {
    await page.getByRole("link", { name: /chat/i }).click();
    await expect(page).toHaveURL(/\/chat/);
  });

  test("should navigate to usage page", async ({ page }) => {
    await page.getByRole("link", { name: /uso/i }).click();
    await expect(page).toHaveURL(/\/usage/);
  });

  test("should navigate to billing page", async ({ page }) => {
    await page.getByRole("link", { name: /facturación/i }).click();
    await expect(page).toHaveURL(/\/billing/);
  });

  test("should show usage alert when near limit", async ({ page }) => {
    // This test assumes the test user is near usage limit
    const alert = page.getByTestId("usage-alert");
    if (await alert.isVisible()) {
      await expect(alert).toContainText(/uso/i);
    }
  });

  test("should be responsive on mobile", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Sidebar should be hidden on mobile
    const sidebar = page.getByTestId("sidebar");
    await expect(sidebar).not.toBeVisible();

    // Menu button should be visible
    await expect(page.getByTestId("mobile-menu-button")).toBeVisible();

    // Click menu to open sidebar
    await page.getByTestId("mobile-menu-button").click();

    // Sidebar should now be visible
    await expect(sidebar).toBeVisible();
  });
});
