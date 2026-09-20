import { test, expect } from '@playwright/test';

const routes = [
  ['/dashboard', 'Mission Command Dashboard'],
  ['/aois', 'Areas'],
  ['/search', 'Semantic'],
  ['/changes', 'Change'],
  ['/velocity', 'Velocity'],
  ['/clusters', 'Cluster'],
  ['/clusters/0', 'Cluster'],
  ['/tiles/43QBA935995', 'Tile'],
  ['/changes/578', 'Change'],
  ['/review', 'Review'],
  ['/audit-log', 'Audit'],
  ['/settings', 'Settings'],
  ['/onboard', 'AOI'],
] as const;

test.describe('Sky Analyst browser certification', () => {
  test('declared routes render without browser or API errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(`console: ${message.text()}`);
    });
    page.on('response', response => {
      if (response.status() >= 500) errors.push(`http ${response.status()}: ${response.url()}`);
    });

    for (const [path, marker] of routes) {
      await page.goto(path, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('body')).toContainText(marker, { timeout: 15000 });
      await expect(page.locator('body')).not.toContainText('Loading...', { timeout: 15000 });
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('body')).toContainText(marker, { timeout: 15000 });
    }

    expect(errors, errors.join('\n')).toEqual([]);
  });

  test('navigation and real workflow context remain usable', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });

    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.getByRole('link', { name: /Surveillance Feed/i }).click();
    await expect(page).toHaveURL(/\/changes$/);
    await expect(page.locator('body')).toContainText(/Change/i);
    await page.goBack({ waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/dashboard$/);
    await page.goForward({ waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/changes$/);
    await page.goto('/clusters/0', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).toContainText(/Cluster/i);
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).toContainText(/Settings/i);
    expect(errors, errors.join('\n')).toEqual([]);
  });

  test('real tile workflow reaches temporal, change, heatmap, discovery, and analyst surfaces', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });

    for (const [path, marker] of [
      ['/dashboard', 'Mission Command Dashboard'],
      ['/aois/navi-mumbai', 'navi-mumbai'],
      ['/search', 'Semantic'],
      ['/tiles/43QBE096610', '43QBE096610'],
      ['/velocity', 'Velocity'],
      ['/changes/501', 'Candidate Evidence'],
      ['/clusters/4', 'Cluster'],
      ['/settings', 'Settings'],
    ] as const) {
      await page.goto(path, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('body')).toContainText(marker, { timeout: 20000 });
      if (path === '/changes/501') {
        await expect(page.locator('body')).toContainText('Sentinel-1', { timeout: 20000 });
        const heatmapButton = page.getByRole('button', { name: /heatmap/i });
        if (await heatmapButton.count()) await heatmapButton.first().click();
      }
    }
    expect(errors, errors.join('\n')).toEqual([]);
  });
});
