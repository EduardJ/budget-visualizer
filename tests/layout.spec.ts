import { expect, test } from '@playwright/test';
import { C, collectErrors, datasetOf, open, shot } from './helpers';

// Layout is identical at every zoom level; zoom only changes what is drawn. Nothing overlaps, no text leaves its box,
// and "fit" shows the whole world of each tab.
test('every tab: no overlaps, no text overflow at five zoom levels, identical layout, fit shows all', async ({ page }, info) => {
  const errs = collectErrors(page);
  await open(page, info);
  expect(await page.evaluate(`${C}.loaded()`), 'only core data parsed at start').toEqual(['core']);
  const summary: Record<string, unknown> = {};
  for (const tab of datasetOf(info).config.tabs.map(t => t.id)) {
    await page.evaluate(`${C}.switchTab("${tab}")`);
    const sig = await page.evaluate(`${C}.layoutSignature()`);
    const zoom: [number, number, number][] = [];
    for (const k of [0.12, 0.3, 0.7, 1.6, 3.0]) {
      await page.evaluate(`${C}.setZoom(${k})`);
      zoom.push([k, await page.evaluate(`${C}.level()`) as number, (await page.evaluate(`${C}.textOverflow()`) as string[]).length]);
    }
    await page.evaluate(`${C}.fitAll()`);
    await page.waitForTimeout(200);
    const fit = await page.evaluate(() => {
      const { S, L } = (window as any).__canvas, c = document.querySelector('#cv') as HTMLCanvasElement;
      return S.x <= 0 && S.y <= 0 && S.x + c.clientWidth / S.k >= L.w && S.y + c.clientHeight / S.k >= L.h;
    });
    await shot(page, info, 'fit_' + tab);
    const identical = sig === await page.evaluate(`${C}.layoutSignature()`);
    const overlaps = (await page.evaluate(`${C}.overlaps()`) as unknown[]).length;
    const overflow = zoom.reduce((a, z) => a + z[2], 0);
    summary[tab] = [identical, overlaps, fit, overflow];
    expect.soft(identical, `${tab}: layout identical across zoom levels`).toBe(true);
    expect.soft(overlaps, `${tab}: overlapping boxes`).toBe(0);
    expect.soft(fit, `${tab}: fit shows the whole world`).toBe(true);
    expect.soft(overflow, `${tab}: text overflow at ${JSON.stringify(zoom)}`).toBe(0);
    expect.soft(zoom.map(z => z[1]), `${tab}: semantic zoom levels`).toEqual([0, 0, 1, 2, 2]);
    expect.soft(await page.locator('#kpis .kpi').count(), `${tab}: headline figures`).toBeGreaterThan(0);
  }
  console.log(JSON.stringify(summary));
  expect(errs).toEqual([]);
});
