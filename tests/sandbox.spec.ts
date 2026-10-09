import { test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { checklist, isKosovo2026, shot, wait } from './helpers';

// Inside a sandboxed iframe with srcdoc (e.g. a chat preview) the History API throws and nothing can be fetched.
// The single-file build must still run, keep in-app back/forward, and stay in Albanian by default.
test('single file in a sandboxed srcdoc iframe', async ({ page }, info) => {
  test.skip(!isKosovo2026(info), 'scenario written for the kosovo-2026 dataset');
  const { ok, report } = checklist();
  const html = readFileSync('dist-single/index.html', 'utf8');
  const errs: string[] = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push(String(e)));
  await page.setContent('<html><body style="margin:0"><iframe id="f" sandbox="allow-scripts allow-popups" style="border:0;width:100vw;height:100vh"></iframe></body></html>');
  await page.evaluate(h => { (document.getElementById('f') as HTMLIFrameElement).srcdoc = h; }, html);
  await wait(page, 2500);
  const fr = page.frames().find(f => f !== page.mainFrame())!;
  ok('runs in about:srcdoc', fr.url() === 'about:srcdoc', fr.url());
  const C = 'window.__canvas';
  await fr.evaluate(`${C}.showNode("dest:central")`); await wait(page, 300);
  await fr.evaluate(`${C}.showNode("org:208")`); await wait(page, 300);
  await fr.evaluate(`${C}.setLang("en")`); await fr.evaluate(`${C}.setFmt("short")`);
  await fr.evaluate(`${C}.startTour("debt",0)`); await wait(page, 400);
  for (let i = 1; i < 11; i++) { await fr.evaluate(`${C}.tourGo(${i})`); await wait(page, 80); }
  await wait(page, 600);
  await shot(page, info, 'sandbox_debt_end');
  await fr.evaluate(`${C}.exitTour()`);
  const nav = await fr.evaluate(() => getComputedStyle(document.getElementById('nav-mem')!).display);
  ok('in-app back/forward shown in sandbox', nav !== 'none', nav);
  await fr.click('#nav-mem [data-nav=back]'); await wait(page, 500);
  const st = await fr.evaluate(() => { const S = (window as any).__canvas.S; return [S.tour && S.tour.id, S.step]; });
  ok('in-app back steps back through the tour', JSON.stringify(st) === '["debt",10]', st);
  for (let i = 0; i < 12; i++) if (!(await fr.isDisabled('#nav-mem [data-nav=back]'))) await fr.click('#nav-mem [data-nav=back]');
  await wait(page, 500);
  const h = (await fr.isVisible('#panel h2')) ? await fr.innerText('#panel h2') : '';
  ok('in-app back reaches first selection', h.includes('Central') || h.includes('Qendror'), h);
  await fr.click('#nav-mem [data-nav=fwd]'); await wait(page, 400);
  ok('in-app forward', (await fr.innerText('#panel h2')).includes('Education'), await fr.innerText('#panel h2'));
  await fr.evaluate(`${C}.setLang("sq")`); await fr.click('#b-recon'); await wait(page, 200);
  const t = await fr.innerText('#recon');
  ok('reconciliation panel in Albanian', t.includes('mospërputhje') && t.includes('Kontrolli'));
  ok('no English finding titles in SQ', !t.includes('Capital projects') && !t.includes('Same municipality') && !t.includes('sum of lines'));
  await shot(page, info, 'sandbox_recon_sq'); await fr.click('#recon [data-x]');
  ok('no errors inside sandbox', errs.length === 0, errs.slice(0, 3));
  report();
});
