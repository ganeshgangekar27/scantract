import { test, expect } from '@playwright/test';

test.describe('Upload Page Screenshots', () => {
  test.beforeEach(async ({ page }) => {
    // Set token before navigation
    await page.addInitScript(() => {
      localStorage.setItem('scantract_token', 'tok');
    });

    // Mock auth endpoint
    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'test@example.com',
          full_name: 'Test User',
        }),
      });
    });

    // Mock contracts list
    await page.route('**/api/contracts/list', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
  });

  test('empty state - desktop light', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'light');
    });
    
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    await page.waitForSelector('text=/upload your contract/i', { timeout: 5000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-empty-desktop-light.png',
      fullPage: true,
    });
  });

  test('empty state - desktop dark', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark');
    });
    
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    await page.waitForSelector('text=/upload your contract/i', { timeout: 5000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-empty-desktop-dark.png',
      fullPage: true,
    });
  });

  test('empty state - mobile light', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'light');
    });
    
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    await page.waitForSelector('text=/upload your contract/i', { timeout: 5000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-empty-mobile-light.png',
      fullPage: true,
    });
  });

  test('empty state - mobile dark', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark');
    });
    
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    await page.waitForSelector('text=/upload your contract/i', { timeout: 5000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-empty-mobile-dark.png',
      fullPage: true,
    });
  });

  test('file selected - desktop light', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'light');
    });
    
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    await page.waitForSelector('input[type="file"]', { timeout: 5000 });
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'rental-agreement.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content'),
    });
    
    await page.waitForSelector('text=/rental-agreement.pdf/i', { timeout: 3000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-selected-desktop-light.png',
      fullPage: true,
    });
  });

  test('file selected - mobile dark', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark');
    });
    
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    await page.waitForSelector('input[type="file"]', { timeout: 5000 });
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'rental-agreement.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content'),
    });
    
    await page.waitForSelector('text=/rental-agreement.pdf/i', { timeout: 3000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-selected-mobile-dark.png',
      fullPage: true,
    });
  });

  test('tracker classifying - desktop light', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'light');
    });
    
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    
    // Mock upload response
    await page.route('**/api/contracts/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contract_id: 999,
          filename: 'test.pdf',
          status: 'uploaded',
        }),
      });
    });

    // Mock status polling - classifying
    await page.route('**/api/contracts/999/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contract_id: 999,
          filename: 'test.pdf',
          uploaded_at: '2024-01-01T00:00:00Z',
          processing_status: 'processing',
          pipeline_stage: 'classifying',
          failed_stage: null,
          error_message: null,
        }),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF'),
    });

    await page.click('button:has-text("Analyze Contract")');
    await page.waitForSelector('text=/classifying/i', { timeout: 5000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-tracker-classifying-desktop-light.png',
      fullPage: true,
    });
  });

  test('tracker failed - mobile dark', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('theme', 'dark');
    });
    
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:5173/upload');
    
    await expect(page).toHaveURL(/\/upload/);
    
    await page.route('**/api/contracts/upload', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contract_id: 999,
          filename: 'test.pdf',
          status: 'uploaded',
        }),
      });
    });

    await page.route('**/api/contracts/999/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contract_id: 999,
          filename: 'test.pdf',
          uploaded_at: '2024-01-01T00:00:00Z',
          processing_status: 'failed',
          pipeline_stage: 'failed',
          failed_stage: 'classifying',
          error_message: 'Daily AI request limit reached',
        }),
      });
    });

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF'),
    });

    await page.click('button:has-text("Analyze Contract")');
    await page.waitForSelector('text=/Daily AI request limit reached/i', { timeout: 5000 });
    
    await page.screenshot({
      path: 'screenshots/batchC2fix/upload-tracker-failed-mobile-dark.png',
      fullPage: true,
    });
  });
});
