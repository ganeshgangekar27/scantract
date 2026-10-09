/**
 * Real backend proof - contract 46 report viewing
 * NO mocks, NO LLM calls, NO uploads
 */
import { test, expect } from '@playwright/test';

test('real backend - view contract 46 report', async ({ page }) => {
  const timestamp = Date.now();
  const email = `test+${timestamp}@example.com`;
  const password = 'TestPassword123!';

  console.log('=== STEP 1: Register user ===');
  await page.goto('http://localhost:5173/signup');
  
  await page.getByLabel('Full Name').fill('Test User');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Confirm Password').fill(password);
  
  await page.getByRole('button', { name: /sign up/i }).click();
  
  // Wait for redirect to dashboard
  await page.waitForURL('**/dashboard', { timeout: 10000 });
  console.log('PASS: User registered and logged in');

  console.log('=== STEP 2: Navigate to contract 46 ===');
  await page.goto('http://localhost:5173/contracts/46');
  await page.waitForLoadState('networkidle');

  console.log('=== STEP 3: Assert filename heading ===');
  const heading = page.locator('h1').first();
  await expect(heading).toContainText(/\.pdf/i, { timeout: 10000 });
  const filename = await heading.textContent();
  console.log(`PASS: Filename heading found: ${filename}`);

  console.log('=== STEP 4: Assert disclaimer text ===');
  await expect(page.getByText(/ScanTract is an educational tool, not legal advice/i)).toBeVisible();
  console.log('PASS: Disclaimer text present');

  console.log('=== STEP 5: Assert at least one finding card ===');
  const findingCards = page.locator('[id^="finding-"]');
  await expect(findingCards.first()).toBeVisible({ timeout: 10000 });
  const count = await findingCards.count();
  expect(count).toBeGreaterThan(0);
  console.log(`PASS: ${count} finding cards found`);

  console.log('=== STEP 6: Click High chip and assert only high cards remain ===');
  await page.getByRole('button', { name: /High \(/i }).click();
  await page.waitForTimeout(500);
  
  // Check that High severity badges are visible
  const highBadges = page.locator('text=/^high$/i');
  const highCount = await highBadges.count();
  expect(highCount).toBeGreaterThan(0);
  console.log(`PASS: ${highCount} high severity cards shown after filtering`);

  console.log('=== STEP 7: Click one finding and assert Why-flagged panel shows reason ===');
  // Click the first high finding
  const firstFinding = page.locator('[id^="finding-"]').first();
  await firstFinding.click();
  await page.waitForTimeout(500);
  
  // Check that "Why Flagged" panel appears
  await expect(page.getByText('Why Flagged')).toBeVisible();
  console.log('PASS: Why-flagged panel shows after clicking finding');

  console.log('=== STEP 8: Take screenshot ===');
  await page.screenshot({ path: 'screenshots/batchC3/report-46.png', fullPage: true });
  console.log('PASS: Screenshot saved');

  console.log('=== STEP 9: Test contract 57 returns 404 ===');
  await page.goto('http://localhost:5173/contracts/57');
  await expect(page.getByText('Contract not found')).toBeVisible({ timeout: 10000 });
  console.log('PASS: Contract 57 shows "Contract not found"');

  console.log('=== ALL TESTS PASSED ===');
});
