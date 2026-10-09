import { expect, type Page, type TestInfo } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { datasetDir, loadDataset, type Dataset } from '../tools/dataset.ts';

export const C = 'window.__canvas';

/** The dataset a test project was built from (project metadata datasetDir, else the build's default). */
export function datasetOf(info: TestInfo): Dataset {
  const dir = info.project.metadata?.datasetDir as string | undefined;
  return loadDataset(dir ? resolve(dir) : datasetDir());
}

/** The kosovo-2026 scenario specs check ids and texts of that document; other datasets get generic.spec. */
export const isKosovo2026 = (info: TestInfo) => datasetOf(info).config.id === 'kosovo-2026';

export async function open(page: Page, info: TestInfo, hash = '') {
  await page.goto((info.project.use.baseURL ?? '') + hash);
  await page.waitForFunction(() => (window as any).__canvas && document.querySelector('#kpis .kpi'));
  await page.evaluate(() => (window as any).__canvas.idle());
}

/** Console errors and warnings and uncaught exceptions, collected for the whole test. */
export function collectErrors(page: Page) {
  const errs: string[] = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  return errs;
}

export const shot = (page: Page, info: TestInfo, name: string) => {
  const dir = join('tests', 'shots', info.project.name);
  mkdirSync(dir, { recursive: true });
  return page.screenshot({ path: join(dir, name + '.png') });
};

/** Named checks in the style of the original suite: every check runs, failures are reported together. */
export function checklist() {
  const rows: [boolean, string, string][] = [];
  return {
    ok(name: string, cond: unknown, detail: unknown = '') {
      rows.push([!!cond, name, String(detail).slice(0, 160)]);
      expect.soft(!!cond, `${name}  (${String(detail).slice(0, 160)})`).toBe(true);
    },
    report() {
      for (const [p, n, d] of rows) console.log(`${p ? 'PASS' : 'FAIL'} | ${n} | ${d}`);
      console.log(`PASSED ${rows.filter(r => r[0]).length} of ${rows.length}`);
    },
  };
}

export async function centerOf(page: Page, id: string): Promise<[number, number]> {
  const s = await page.evaluate(i => (window as any).__canvas.screenOf(i), id);
  return [s.x + s.w / 2, s.y + s.h / 2];
}

export const stageTop = (page: Page) => page.evaluate(() => document.querySelector('#stage')!.getBoundingClientRect().top);
export const idle = (page: Page) => page.evaluate(() => (window as any).__canvas.idle());
export const wait = (page: Page, ms: number) => page.waitForTimeout(ms);
