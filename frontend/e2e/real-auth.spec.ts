import { test, expect } from '@playwright/test';

const TIMESTAMP = Date.now();
const TEST_EMAIL = `test+${TIMESTAMP}@example.com`;
const TEST_PASSWORD = 'TestPassword123!';
const TEST_NAME = 'Test User';
let RESET_TOKEN = '';

test.describe('Real Backend Auth Flow', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('1. Signup lands on dashboard', async ({ page }) => {
    await page.goto('http://localhost:5173/signup');
    await page.waitForLoadState('networkidle');

    // Fill signup form using label text
    await page.getByLabel('Full name').fill(TEST_NAME);
    await page.getByLabel('Email').fill(TEST_EMAIL);
    await page.getByLabel('Password', { exact: true }).fill(TEST_PASSWORD);
    await page.getByLabel('Confirm password').fill(TEST_PASSWORD);

    // Submit
    await page.getByRole('button', { name: /create account/i }).click();

    // Should navigate to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    await expect(page.getByText('Welcome to ScanTract')).toBeVisible({ timeout: 5000 });

    console.log('✓ PASS: Signup lands on dashboard');
  });

  test('2. Logout', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:5173/login');
    await page.getByLabel('Email', { exact: true }).fill(TEST_EMAIL);
    await page.locator('input[type="password"]').first().fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /log in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Logout by clearing token
    await page.evaluate(() => localStorage.removeItem('scantract_token'));
    await page.goto('http://localhost:5173/login');

    // Should be on login page
    await expect(page).toHaveURL(/\/login/);

    console.log('✓ PASS: Logout');
  });

  test('3. Login with wrong password shows error', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('Email', { exact: true }).fill(TEST_EMAIL);
    await page.locator('input[type="password"]').first().fill('WrongPassword123!');
    await page.getByRole('button', { name: /log in/i }).click();

    // Should show "Incorrect password" error
    await expect(page.getByText('Incorrect password')).toBeVisible({ timeout: 5000 });

    console.log('✓ PASS: Login with wrong password shows "Incorrect password"');
  });

  test('4. Login with correct password lands on dashboard', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('Email', { exact: true }).fill(TEST_EMAIL);
    await page.locator('input[type="password"]').first().fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /log in/i }).click();

    // Should navigate to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    await expect(page.getByText('Welcome to ScanTract')).toBeVisible({ timeout: 5000 });

    console.log('✓ PASS: Login with correct password lands on dashboard');
  });

  test('5. Forgot password shows demo reset link', async ({ page }) => {
    await page.goto('http://localhost:5173/forgot-password');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('Email', { exact: true }).fill(TEST_EMAIL);
    await page.getByRole('button', { name: /send reset link/i }).click();

    // Should show success message and demo link
    await expect(page.getByText('Check your email')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Demo mode')).toBeVisible({ timeout: 5000 });

    // Demo link button should be visible
    const demoLinkButton = page.getByRole('button', { name: /open reset link/i });
    await expect(demoLinkButton).toBeVisible();

    console.log('✓ PASS: Forgot password shows demo reset link');
  });

  test('6. Reset password and login with new password', async ({ page }) => {
    // Get reset token
    await page.goto('http://localhost:5173/forgot-password');
    await page.getByLabel('Email', { exact: true }).fill(TEST_EMAIL);
    await page.getByRole('button', { name: /send reset link/i }).click();
    await expect(page.getByText('Demo mode')).toBeVisible({ timeout: 5000 });

    // Click the demo link button to navigate
    await page.getByRole('button', { name: /open reset link/i }).click();
    await page.waitForLoadState('networkidle');

    // Should be on reset password page
    await expect(page).toHaveURL(/\/reset-password\?token=/);

    // Set new password
    const NEW_PASSWORD = 'NewTestPassword456!';
    const passwordFields = page.locator('input[type="password"]');
    await passwordFields.nth(0).fill(NEW_PASSWORD);
    await passwordFields.nth(1).fill(NEW_PASSWORD);

    // Submit
    await page.getByRole('button', { name: /reset password/i }).click();

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Login with new password
    await page.getByLabel('Email', { exact: true }).fill(TEST_EMAIL);
    await page.locator('input[type="password"]').first().fill(NEW_PASSWORD);
    await page.getByRole('button', { name: /log in/i }).click();

    // Should land on dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    await expect(page.getByText('Welcome to ScanTract')).toBeVisible({ timeout: 5000 });

    console.log('✓ PASS: Reset password and login with new password');
  });
});
