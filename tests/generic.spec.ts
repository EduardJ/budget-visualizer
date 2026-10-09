import { test } from '@playwright/test';
import { C, checklist, collectErrors, datasetOf, idle, open, shot, wait } from './helpers';

// What must hold for any dataset, with ids and texts taken from the dataset itself: every tab renders, headline figures
// open their source, panels cite the PDF, every language has its title, search finds names, the reconciliation lists
// every check, tours run, deep links restore.
test('any dataset: tabs, panels, sources, languages, search, reconciliation, tours, deep links', async ({ page }, info) => {
  const { ok, report } = checklist();
  const errs = collectErrors(page);
  const { config: cfg, data } = datasetOf(info);
  const src = cfg.sourceLang, lang0 = cfg.langs[0];
  const name = (id: string) => String(data.nodes.find(n => n.id === id)?.[`name_${lang0}`] ?? data.nodes.find(n => n.id === id)?.[`name_${src}`]);
  await open(page, info);

  for (const t of cfg.tabs) {
    await page.click(`#tabs [data-tab="${t.id}"]`); await idle(page);
    ok(`tab ${t.id}: selected and in the URL`, (await page.evaluate(`${C}.S.tab`)) === t.id && (t === cfg.tabs[0] || (await page.evaluate(() => location.hash)).includes('tab=' + t.id)));
    ok(`tab ${t.id}: boxes laid out`, (await page.evaluate(`${C}.L.boxes.length`) as number) > 1);
    const kpis = await page.locator('#kpis .kpi').count();
    ok(`tab ${t.id}: headline figures`, kpis > 0 || !data.kpis.some(k => k.tab === t.id) && t.layout !== 'checks', kpis);
    await shot(page, info, 'generic_' + t.id);
  }

  // a node from every tab that draws nodes: panel title, amount, a cited source with a PDF link
  const picks = cfg.tabs.flatMap(t => t.layout === 'sankey' ? [t.columns[0].nodes[0]] : t.layout === 'cards' || t.layout === 'ranking'
    ? [data.nodes.filter(n => n.kind === t.kind).sort((a, b) => b.amount - a.amount)[0]?.id] : []).filter(Boolean) as string[];
  for (const id of picks) {
    await page.evaluate(`${C}.showNode(${JSON.stringify(id)})`);
    ok(`panel for ${id}: name`, (await page.innerText('#panel h2')).startsWith(name(id)), await page.innerText('#panel h2'));
    const href = await page.getAttribute('#panel .ref .acts a', 'href');
    ok(`panel for ${id}: cites the PDF`, href?.startsWith(cfg.pdf + '#page='), href);
    ok(`panel for ${id}: hash`, (await page.evaluate(() => location.hash)).includes('node=' + encodeURIComponent(id)));
  }
  const flow = data.flows.find(f => f.kind === 'hard');
  if (flow) {
    await page.evaluate(`${C}.showFlow(${JSON.stringify(flow.id)})`);
    ok('flow panel', (await page.innerText('#panel h2')).includes('→'), await page.innerText('#panel h2'));
  }
  await page.click('#panel [data-close]');

  for (const l of cfg.langs) {
    await page.click('#l-' + l); await wait(page, 100);
    ok(`language ${l}: title`, (await page.innerText('#t-title')) === cfg.strings[l].title, await page.innerText('#t-title'));
  }
  await page.click('#l-' + lang0);

  const word = name(picks[picks.length - 1] ?? data.nodes[0].id).split(' ')[0];
  await page.fill('#q', word); await wait(page, 200);
  ok(`search "${word}"`, (await page.innerText('#results')).includes(word), (await page.innerText('#results')).slice(0, 80));
  await page.keyboard.press('Enter'); await idle(page);
  ok('search Enter opens a panel', await page.isVisible('#panel h2'));

  await page.click('#b-recon');
  const rows = await page.locator('#recon table >> nth=0 >> tr').count();
  ok('reconciliation lists every check', rows === data.checks.length + 1, rows);
  await page.click('#recon [data-x]');

  for (const tr of data.tours) {
    await page.evaluate(`${C}.startTour(${JSON.stringify(tr.id)}, 0)`);
    for (let s = 0; s < tr.steps.length; s++) await page.evaluate(`${C}.tourGo(${s})`);
    ok(`tour ${tr.id}: all ${tr.steps.length} steps`, (await page.innerText('#tourbar .t span')).includes(`${tr.steps.length}/${tr.steps.length}`));
    await page.click('#tourbar [data-t=exit]');
  }

  const deep = picks[picks.length - 1];
  if (deep) {
    const p2 = await page.context().newPage();
    await open(p2, info, '#node=' + encodeURIComponent(deep)); await wait(p2, 300);
    ok('deep link restores the node', (await p2.innerText('#panel h2')).startsWith(name(deep)), await p2.innerText('#panel h2'));
  }
  ok('no console errors', errs.length === 0, errs);
  report();
});
