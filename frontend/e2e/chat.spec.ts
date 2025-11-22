import { test, expect } from "@playwright/test";

test.describe("Chat", () => {
  test.use({ storageState: ".playwright/.auth/user.json" });

  test.beforeEach(async ({ page }) => {
    await page.goto("/chat");
  });

  test("should display chat interface", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /chat/i })).toBeVisible();

    // Agent selector should be visible
    await expect(page.getByTestId("agent-selector")).toBeVisible();

    // Chat input should be visible
    await expect(page.getByPlaceholder(/escribe un mensaje/i)).toBeVisible();
  });

  test("should select an agent", async ({ page }) => {
    await page.getByTestId("agent-selector").click();

    // Select first agent
    await page.getByRole("option").first().click();

    // Agent should be selected
    await expect(page.getByTestId("selected-agent")).toBeVisible();
  });

  test("should send a message", async ({ page }) => {
    // Select agent first
    await page.getByTestId("agent-selector").click();
    await page.getByRole("option").first().click();

    // Type message
    const input = page.getByPlaceholder(/escribe un mensaje/i);
    await input.fill("Hello, this is a test message");

    // Send message
    await page.getByRole("button", { name: /enviar/i }).click();

    // Message should appear in chat
    await expect(page.getByText("Hello, this is a test message")).toBeVisible();

    // Wait for response (with timeout)
    await expect(page.getByTestId("assistant-message")).toBeVisible({ timeout: 30000 });
  });

  test("should show typing indicator while waiting for response", async ({ page }) => {
    // Select agent
    await page.getByTestId("agent-selector").click();
    await page.getByRole("option").first().click();

    // Send message
    await page.getByPlaceholder(/escribe un mensaje/i).fill("Test message");
    await page.getByRole("button", { name: /enviar/i }).click();

    // Typing indicator should appear
    await expect(page.getByTestId("typing-indicator")).toBeVisible();
  });

  test("should display conversation history", async ({ page }) => {
    // Check for conversation list
    await expect(page.getByTestId("conversation-list")).toBeVisible();
  });

  test("should create new conversation", async ({ page }) => {
    await page.getByRole("button", { name: /nueva conversación/i }).click();

    // Chat should be cleared
    await expect(page.getByTestId("chat-messages")).toBeEmpty();
  });

  test("should load previous conversation", async ({ page }) => {
    // Click on a conversation in the list
    const conversations = page.getByTestId("conversation-item");
    const count = await conversations.count();

    if (count > 0) {
      await conversations.first().click();

      // Messages should load
      await expect(page.getByTestId("chat-messages")).not.toBeEmpty();
    }
  });

  test("should delete conversation", async ({ page }) => {
    const conversations = page.getByTestId("conversation-item");
    const count = await conversations.count();

    if (count > 0) {
      // Hover over conversation to show delete button
      await conversations.first().hover();
      await conversations.first().getByRole("button", { name: /eliminar/i }).click();

      // Confirm deletion
      await page.getByRole("button", { name: /confirmar/i }).click();

      // Conversation should be removed
      const newCount = await conversations.count();
      expect(newCount).toBeLessThan(count);
    }
  });

  test("should copy message to clipboard", async ({ page }) => {
    // Select agent and send message
    await page.getByTestId("agent-selector").click();
    await page.getByRole("option").first().click();
    await page.getByPlaceholder(/escribe un mensaje/i).fill("Test message to copy");
    await page.getByRole("button", { name: /enviar/i }).click();

    // Wait for message to appear
    await expect(page.getByText("Test message to copy")).toBeVisible();

    // Click copy button
    await page.getByTestId("user-message").first().hover();
    await page.getByRole("button", { name: /copiar/i }).first().click();

    // Toast should appear confirming copy
    await expect(page.getByText(/copiado/i)).toBeVisible();
  });

  test("should handle empty message", async ({ page }) => {
    // Select agent
    await page.getByTestId("agent-selector").click();
    await page.getByRole("option").first().click();

    // Try to send empty message
    await page.getByRole("button", { name: /enviar/i }).click();

    // Button should be disabled or nothing should happen
    const messages = page.getByTestId("chat-messages");
    await expect(messages).toBeEmpty();
  });

  test("should handle very long message", async ({ page }) => {
    // Select agent
    await page.getByTestId("agent-selector").click();
    await page.getByRole("option").first().click();

    // Send very long message
    const longMessage = "A".repeat(5000);
    await page.getByPlaceholder(/escribe un mensaje/i).fill(longMessage);
    await page.getByRole("button", { name: /enviar/i }).click();

    // Message should be truncated or handled gracefully
    await expect(page.getByTestId("user-message")).toBeVisible();
  });

  test("should support keyboard shortcuts", async ({ page }) => {
    // Select agent
    await page.getByTestId("agent-selector").click();
    await page.getByRole("option").first().click();

    // Type message
    const input = page.getByPlaceholder(/escribe un mensaje/i);
    await input.fill("Test keyboard shortcut");

    // Press Enter to send
    await input.press("Enter");

    // Message should be sent
    await expect(page.getByText("Test keyboard shortcut")).toBeVisible();
  });

  test("should be responsive on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    // Chat interface should still work
    await expect(page.getByPlaceholder(/escribe un mensaje/i)).toBeVisible();

    // Conversation list might be hidden in drawer
    const drawer = page.getByTestId("conversations-drawer");
    if (await drawer.isVisible()) {
      // Mobile drawer implementation
      await page.getByRole("button", { name: /conversaciones/i }).click();
      await expect(page.getByTestId("conversation-list")).toBeVisible();
    }
  });
});
