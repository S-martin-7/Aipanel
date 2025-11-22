import { test, expect } from "@playwright/test";

test.describe("Agents Management", () => {
  test.use({ storageState: ".playwright/.auth/user.json" });

  test.beforeEach(async ({ page }) => {
    await page.goto("/agents");
  });

  test("should display agents list", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /agentes/i })).toBeVisible();

    // Check for create button
    await expect(page.getByRole("button", { name: /crear agente/i })).toBeVisible();
  });

  test("should open create agent modal", async ({ page }) => {
    await page.getByRole("button", { name: /crear agente/i }).click();

    // Modal should be visible
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText(/nuevo agente/i)).toBeVisible();

    // Form fields should be present
    await expect(page.getByLabel(/nombre/i)).toBeVisible();
    await expect(page.getByLabel(/descripción/i)).toBeVisible();
  });

  test("should create a new agent", async ({ page }) => {
    await page.getByRole("button", { name: /crear agente/i }).click();

    // Fill form
    await page.getByLabel(/nombre/i).fill("Test Agent E2E");
    await page.getByLabel(/descripción/i).fill("Agent created by E2E test");

    // Select model
    await page.getByLabel(/modelo/i).click();
    await page.getByRole("option", { name: /gpt-4/i }).click();

    // Fill system prompt
    await page.getByLabel(/system prompt/i).fill("You are a helpful assistant for testing.");

    // Submit
    await page.getByRole("button", { name: /crear$/i }).click();

    // Wait for modal to close and agent to appear in list
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.getByText("Test Agent E2E")).toBeVisible();
  });

  test("should edit an existing agent", async ({ page }) => {
    // Find first agent card and click edit
    const agentCard = page.getByTestId("agent-card").first();
    await agentCard.getByRole("button", { name: /editar/i }).click();

    // Modal should open with existing data
    await expect(page.getByRole("dialog")).toBeVisible();

    // Modify description
    const descriptionField = page.getByLabel(/descripción/i);
    await descriptionField.clear();
    await descriptionField.fill("Updated description via E2E test");

    // Save
    await page.getByRole("button", { name: /guardar/i }).click();

    // Modal should close
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("should delete an agent", async ({ page }) => {
    // Find test agent created earlier
    const agentCard = page.getByText("Test Agent E2E").locator("..").locator("..");

    // Click delete button
    await agentCard.getByRole("button", { name: /eliminar/i }).click();

    // Confirm deletion
    await expect(page.getByRole("alertdialog")).toBeVisible();
    await page.getByRole("button", { name: /confirmar/i }).click();

    // Agent should be removed
    await expect(page.getByText("Test Agent E2E")).not.toBeVisible();
  });

  test("should toggle agent status", async ({ page }) => {
    const agentCard = page.getByTestId("agent-card").first();
    const statusToggle = agentCard.getByRole("switch");

    // Get initial state
    const initialState = await statusToggle.isChecked();

    // Toggle
    await statusToggle.click();

    // State should change
    await expect(statusToggle).toBeChecked({ checked: !initialState });
  });

  test("should navigate to agent playground", async ({ page }) => {
    const agentCard = page.getByTestId("agent-card").first();
    await agentCard.getByRole("button", { name: /probar/i }).click();

    await expect(page).toHaveURL(/\/playground/);
  });

  test("should show agent details", async ({ page }) => {
    const agentCard = page.getByTestId("agent-card").first();
    await agentCard.click();

    // Agent details should be visible
    await expect(page.getByText(/configuración/i)).toBeVisible();
    await expect(page.getByText(/estadísticas/i)).toBeVisible();
  });

  test("should filter agents by status", async ({ page }) => {
    // Click status filter
    await page.getByRole("combobox", { name: /estado/i }).click();
    await page.getByRole("option", { name: /activo/i }).click();

    // Should only show active agents
    const agents = page.getByTestId("agent-card");
    const count = await agents.count();

    for (let i = 0; i < count; i++) {
      await expect(agents.nth(i).getByText(/activo/i)).toBeVisible();
    }
  });

  test("should search agents by name", async ({ page }) => {
    await page.getByPlaceholder(/buscar/i).fill("Test");

    // Wait for search results
    await page.waitForTimeout(500);

    // All visible agents should contain "Test"
    const agents = page.getByTestId("agent-card");
    const count = await agents.count();

    if (count > 0) {
      for (let i = 0; i < count; i++) {
        await expect(agents.nth(i)).toContainText(/test/i);
      }
    }
  });
});
