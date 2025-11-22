import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.describe("Login Page", () => {
    test("should display login form", async ({ page }) => {
      await page.goto("/login");

      await expect(page.getByRole("heading", { name: /iniciar sesión/i })).toBeVisible();
      await expect(page.getByLabel("Email")).toBeVisible();
      await expect(page.getByLabel("Contraseña")).toBeVisible();
      await expect(page.getByRole("button", { name: /iniciar sesión/i })).toBeVisible();
    });

    test("should show error with invalid credentials", async ({ page }) => {
      await page.goto("/login");

      await page.getByLabel("Email").fill("invalid@example.com");
      await page.getByLabel("Contraseña").fill("wrongpassword");
      await page.getByRole("button", { name: /iniciar sesión/i }).click();

      await expect(page.getByText(/credenciales inválidas/i)).toBeVisible();
    });

    test("should show validation errors for empty fields", async ({ page }) => {
      await page.goto("/login");

      await page.getByRole("button", { name: /iniciar sesión/i }).click();

      await expect(page.getByText(/email es requerido/i)).toBeVisible();
    });

    test("should redirect to dashboard after successful login", async ({ page }) => {
      await page.goto("/login");

      await page.getByLabel("Email").fill("test@example.com");
      await page.getByLabel("Contraseña").fill("testpassword123");
      await page.getByRole("button", { name: /iniciar sesión/i }).click();

      await page.waitForURL("/dashboard");
      await expect(page).toHaveURL("/dashboard");
    });
  });

  test.describe("Logout", () => {
    test.use({ storageState: ".playwright/.auth/user.json" });

    test("should logout successfully", async ({ page }) => {
      await page.goto("/dashboard");

      // Click user menu
      await page.getByTestId("user-menu").click();

      // Click logout
      await page.getByRole("button", { name: /cerrar sesión/i }).click();

      // Should redirect to login
      await page.waitForURL("/login");
      await expect(page).toHaveURL("/login");
    });
  });

  test.describe("Protected Routes", () => {
    test("should redirect to login when not authenticated", async ({ page }) => {
      // Clear any stored auth
      await page.context().clearCookies();

      await page.goto("/dashboard");

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });

    test("should access dashboard when authenticated", async ({ page }) => {
      // Use stored auth
      await page.goto("/login");
      await page.getByLabel("Email").fill("test@example.com");
      await page.getByLabel("Contraseña").fill("testpassword123");
      await page.getByRole("button", { name: /iniciar sesión/i }).click();

      await page.waitForURL("/dashboard");
      await expect(page.getByText(/dashboard/i)).toBeVisible();
    });
  });
});
