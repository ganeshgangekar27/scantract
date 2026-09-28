import { test } from '@playwright/test';

test('reproduce envelope bug by navigating directly to /report/1', async ({ page }) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', (error) => {
    pageErrors.push(error.message);
  });

  // Navigate directly to report page
  await page.goto('http://localhost:3000/report/1');
  await page.waitForLoadState('networkidle');
  
  // Wait a bit for React to render
  await page.waitForTimeout(2000);
  
  // Screenshot
  await page.screenshot({ path: 'screenshots/reproduce-report-1.png', fullPage: true });
  
  // Get visible text
  const bodyText = await page.locator('body').innerText();
  console.log('=== VISIBLE TEXT (first 1500 chars) ===');
  console.log(bodyText.substring(0, 1500));
  
  console.log('\n=== CONSOLE ERRORS ===');
  if (consoleErrors.length > 0) {
    consoleErrors.forEach((err, i) => console.log(`${i + 1}. ${err}`));
  } else {
    console.log('None');
  }
  
  console.log('\n=== PAGE ERRORS ===');
  if (pageErrors.length > 0) {
    pageErrors.forEach((err, i) => console.log(`${i + 1}. ${err}`));
  } else {
    console.log('None');
  }
});
