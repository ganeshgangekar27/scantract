import { test, expect } from '@playwright/test';

test.describe('ScanTract Frontend Smoke Test', () => {
  test('should load home page, list contracts, and navigate to report', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const failedRequests: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        // Ignore 404s for favicon and other assets
        if (!msg.text().includes('404')) {
          consoleErrors.push(msg.text());
        }
      }
    });

    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
    });

    page.on('requestfailed', (request) => {
      failedRequests.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
    });

    // === HOME PAGE ===
    await page.goto('http://localhost:3000/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/home.png', fullPage: true });

    // Assert: List has at least one link
    const contractLinks = page.locator('a[href*="/report/"]');
    const linkCount = await contractLinks.count();
    expect(linkCount, 'Should have at least one contract link').toBeGreaterThan(0);

    // Find first completed contract
    let completedLinkIndex = -1;
    for (let i = 0; i < linkCount; i++) {
      const linkText = await contractLinks.nth(i).innerText();
      if (linkText.includes('Completed')) {
        completedLinkIndex = i;
        break;
      }
    }
    
    expect(completedLinkIndex, 'Should have at least one completed contract').toBeGreaterThanOrEqual(0);

    // === NAVIGATE TO REPORT ===
    await contractLinks.nth(completedLinkIndex).click();
    await page.waitForLoadState('networkidle');
    
    // Assert: URL landed on /report/:id
    const url = page.url();
    expect(url).toMatch(/\/report\/\d+/);
    
    await page.screenshot({ path: 'screenshots/report-1.png', fullPage: true });

    // === VERIFY REPORT CONTENT (for contract 1) ===
    if (url.includes('/report/1')) {
      // Assert: Shows risky findings count (4)
      const riskyText = await page.locator('body').innerText();
      expect(riskyText).toContain('High:');
      
      // Assert: Has severity badges visible
      const severityBadges = page.locator('text=/HIGH|MEDIUM|LOW/i');
      expect(await severityBadges.count()).toBeGreaterThan(0);
      
      // Assert: Shows explanation text
      const bodyText = await page.locator('body').innerText();
      expect(bodyText.length).toBeGreaterThan(500); // Substantial content
    }

    // === TEST HARD REFRESH ===
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    const refreshedText = await page.locator('body').innerText();
    expect(refreshedText.length, 'Page should still render after refresh').toBeGreaterThan(500);

    // === TEST 404 ERROR HANDLING ===
    await page.goto('http://localhost:3000/report/9999');
    await page.waitForLoadState('networkidle');
    const errorPageText = await page.locator('body').innerText();
    expect(errorPageText).toMatch(/error|not found|failed/i);
    expect(errorPageText.length, '404 should show readable error, not blank page').toBeGreaterThan(10);

    // === ASSERTIONS ===
    expect(consoleErrors, 'Should have no console errors').toHaveLength(0);
    expect(pageErrors, 'Should have no page errors').toHaveLength(0);
    expect(failedRequests, 'Should have no failed requests').toHaveLength(0);
  });
});
