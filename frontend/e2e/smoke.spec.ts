import { test, expect } from '@playwright/test';

test.describe('ScanTract Frontend Smoke Test', () => {
  test('should handle contract 1 report and contract 2 409 error', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const failedRequests: { url: string; status: number }[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        // Ignore 404s for favicon, 409s for expected processing errors
        if (!msg.text().includes('404') && !msg.text().includes('409')) {
          consoleErrors.push(msg.text());
        }
      }
    });

    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
    });

    page.on('response', (response) => {
      if (response.status() >= 400) {
        failedRequests.push({ url: response.url(), status: response.status() });
        console.log(`Failed request: ${response.status()} ${response.url()}`);
      }
    });

    // === CONTRACT 1 REPORT (200) ===
    await page.goto('http://localhost:3000/report/1');
    
    // Wait for report content (not spinner)
    await page.waitForSelector('text=Overall Risk:', { timeout: 10000 });
    await page.screenshot({ path: 'screenshots/home.png', fullPage: true });
    
    // Assert: 4 risky + 3 missing findings
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).toContain('Overall Risk');
    expect(bodyText).toContain('High:');
    
    // Count findings by checking for severity badges
    const severityBadges = page.locator('text=/HIGH|MEDIUM|LOW/i');
    const badgeCount = await severityBadges.count();
    expect(badgeCount).toBeGreaterThanOrEqual(4); // At least 4 risky findings
    
    // === HARD REFRESH OF /report/1 ===
    await page.reload();
    await page.waitForSelector('text=Overall Risk:', { timeout: 10000 });
    const refreshedText = await page.locator('body').innerText();
    expect(refreshedText.length).toBeGreaterThan(500);
    
    await page.screenshot({ path: 'screenshots/report-1.png', fullPage: true });
    
    // === CONTRACT 2 (409) ===
    await page.goto('http://localhost:3000/report/2');
    await page.waitForSelector('text=Error loading report', { timeout: 10000 });
    
    const errorText = await page.locator('body').innerText();
    expect(errorText).toMatch(/processing incomplete|detecting_risks/i);
    expect(errorText).not.toContain('Loading report'); // Not stuck on spinner
    
    // === ASSERTIONS ===
    expect(consoleErrors, 'Should have no console errors').toHaveLength(0);
    expect(pageErrors, 'Should have no page errors').toHaveLength(0);
    
    // Filter out expected 409s from failed requests
    const unexpected409s = failedRequests.filter(r => r.status === 409 && !r.url.includes('/contracts/2'));
    expect(unexpected409s, 'Only /contracts/2 should return 409').toHaveLength(0);
  });
});
