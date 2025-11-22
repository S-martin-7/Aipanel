import { test as setup, expect } from "@playwright/test";
import path from "path";

const authFile = path.join(__dirname, "../.playwright/.auth/user.json");

/**
 * Authentication setup - runs before all tests
 * Logs in and saves the authentication state
 */
setup("authenticate", async ({ page }) => {
  // Go to login page
  await page.goto("/login");

  // Fill in credentials
  await page.getByLabel("Email").fill("test@example.com");
  await page.getByLabel("Contraseña").fill("testpassword123");

  // Click login button
  await page.getByRole("button", { name: /iniciar sesión/i }).click();

  // Wait for navigation to dashboard
  await page.waitForURL("/dashboard");

  // Verify we're logged in
  await expect(page.getByText(/dashboard/i)).toBeVisible();

  // Save authentication state
  await page.context().storageState({ path: authFile });
});

setup.describe.configure({ mode: "serial" });
