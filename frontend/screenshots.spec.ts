import { test, expect, type Page } from '@playwright/test';

const DESKTOP_VIEWPORT = { width: 1440, height: 900 };
const MOBILE_VIEWPORT = { width: 390, height: 844 };

async function mockAuthAPI(page: Page) {
  await page.route('**/api/auth/**', (route) => {
    const url = route.request().url();
    
    if (url.includes('/register')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-token',
          token_type: 'bearer',
          user: { id: 1, email: 'test@example.com', full_name: 'Test User' }
        })
      });
    } else if (url.includes('/login')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-token',
          token_type: 'bearer'
        })
      });
    } else if (url.includes('/forgot-password')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Reset link sent',
          demo_reset_link: 'http://localhost:5173/reset-password?token=demo-123'
        })
      });
    } else if (url.includes('/reset-password')) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Password reset successfully' })
      });
    } else {
      route.continue();
    }
  });
}

test.describe('Auth Screens - Light Mode - Desktop', () => {
  test.use({ viewport: DESKTOP_VIEWPORT, colorScheme: 'light' });

  test('login page', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/login-light-desktop.png', fullPage: true });
  });

  test('signup page with errors', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/signup');
    await page.fill('input[type="email"]', 'invalid-email');
    await page.fill('input[type="password"]', 'short');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'frontend/screenshots/batchA/signup-errors-light-desktop.png', fullPage: true });
  });

  test('forgot-password success with demo', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/forgot-password');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Demo mode');
    await page.screenshot({ path: 'frontend/screenshots/batchA/forgot-success-light-desktop.png', fullPage: true });
  });

  test('reset-password expired link', async ({ page }) => {
    await page.route('**/api/auth/reset-password', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Password reset link has expired' })
      });
    });
    
    await page.goto('http://localhost:5173/reset-password');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/reset-expired-light-desktop.png', fullPage: true });
  });

  test('dashboard placeholder', async ({ page }) => {
    await mockAuthAPI(page);
    // Set token to bypass auth
    await page.goto('http://localhost:5173/login');
    await page.evaluate(() => localStorage.setItem('scantract_token', 'mock-token'));
    await page.goto('http://localhost:5173/dashboard');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/dashboard-light-desktop.png', fullPage: true });
  });
});

test.describe('Auth Screens - Dark Mode - Desktop', () => {
  test.use({ viewport: DESKTOP_VIEWPORT, colorScheme: 'dark' });

  test('login page', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/login-dark-desktop.png', fullPage: true });
  });

  test('signup page with errors', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/signup');
    await page.fill('input[type="email"]', 'invalid-email');
    await page.fill('input[type="password"]', 'short');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'frontend/screenshots/batchA/signup-errors-dark-desktop.png', fullPage: true });
  });

  test('forgot-password success with demo', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/forgot-password');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Demo mode');
    await page.screenshot({ path: 'frontend/screenshots/batchA/forgot-success-dark-desktop.png', fullPage: true });
  });

  test('reset-password expired link', async ({ page }) => {
    await page.route('**/api/auth/reset-password', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Password reset link has expired' })
      });
    });
    
    await page.goto('http://localhost:5173/reset-password');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/reset-expired-dark-desktop.png', fullPage: true });
  });

  test('dashboard placeholder', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.evaluate(() => localStorage.setItem('scantract_token', 'mock-token'));
    await page.goto('http://localhost:5173/dashboard');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/dashboard-dark-desktop.png', fullPage: true });
  });
});

test.describe('Auth Screens - Light Mode - Mobile', () => {
  test.use({ viewport: MOBILE_VIEWPORT, colorScheme: 'light' });

  test('login page', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/login-light-mobile.png', fullPage: true });
  });

  test('signup page with errors', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/signup');
    await page.fill('input[type="email"]', 'invalid-email');
    await page.fill('input[type="password"]', 'short');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'frontend/screenshots/batchA/signup-errors-light-mobile.png', fullPage: true });
  });

  test('forgot-password success with demo', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/forgot-password');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Demo mode');
    await page.screenshot({ path: 'frontend/screenshots/batchA/forgot-success-light-mobile.png', fullPage: true });
  });

  test('reset-password expired link', async ({ page }) => {
    await page.route('**/api/auth/reset-password', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Password reset link has expired' })
      });
    });
    
    await page.goto('http://localhost:5173/reset-password');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/reset-expired-light-mobile.png', fullPage: true });
  });

  test('dashboard placeholder', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.evaluate(() => localStorage.setItem('scantract_token', 'mock-token'));
    await page.goto('http://localhost:5173/dashboard');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/dashboard-light-mobile.png', fullPage: true });
  });
});

test.describe('Auth Screens - Dark Mode - Mobile', () => {
  test.use({ viewport: MOBILE_VIEWPORT, colorScheme: 'dark' });

  test('login page', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/login-dark-mobile.png', fullPage: true });
  });

  test('signup page with errors', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/signup');
    await page.fill('input[type="email"]', 'invalid-email');
    await page.fill('input[type="password"]', 'short');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'frontend/screenshots/batchA/signup-errors-dark-mobile.png', fullPage: true });
  });

  test('forgot-password success with demo', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/forgot-password');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Demo mode');
    await page.screenshot({ path: 'frontend/screenshots/batchA/forgot-success-dark-mobile.png', fullPage: true });
  });

  test('reset-password expired link', async ({ page }) => {
    await page.route('**/api/auth/reset-password', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Password reset link has expired' })
      });
    });
    
    await page.goto('http://localhost:5173/reset-password');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/reset-expired-dark-mobile.png', fullPage: true });
  });

  test('dashboard placeholder', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('http://localhost:5173/login');
    await page.evaluate(() => localStorage.setItem('scantract_token', 'mock-token'));
    await page.goto('http://localhost:5173/dashboard');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'frontend/screenshots/batchA/dashboard-dark-mobile.png', fullPage: true });
  });
});
