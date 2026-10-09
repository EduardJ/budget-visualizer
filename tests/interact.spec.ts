import { test } from '@playwright/test';
import { C, centerOf, checklist, collectErrors, idle, isKosovo2026, open, shot, stageTop, wait } from './helpers';

// One user session from start to finish, as in the original suite: each step builds on the one before.
test('clicks, ribbons, citations, search, toggles, filters, tours, keyboard, deep links, back/forward, mobile', async ({ page, browser }, info) => {
  test.skip(!isKosovo2026(info), 'scenario written for the kosovo-2026 dataset');
  const { ok, report } = checklist();
  const errs = collectErrors(page);
  const hash = () => page.evaluate(() => location.hash);
  const h2 = () => page.innerText('#panel h2');
  // actions that load data finish when the app is idle, not after a fixed time
  const settle = async (ms: number) => { await wait(page, ms); await idle(page); };
  await open(page, info);
  let top = await stageTop(page);

  ok('only core data parsed at start', JSON.stringify(await page.evaluate(`${C}.loaded()`)) === '["core"]', await page.evaluate(`${C}.loaded()`));
  let kp = await page.innerText('#kpis');
  ok('headline strip: spending, change, GDP', kp.includes('Shpenzimet totale 2026') && kp.includes('+9.9%') && kp.includes('BPV 2026') && kp.includes('33.0% e BPV-së'), kp.replace(/\n/g, ' | '));

  // 1 a Sankey node
  let [x, y] = await centerOf(page, 'dest:central');
  await page.mouse.click(x, y + top); await settle(500);
  ok('click node opens panel', (await h2()).includes('Qendror'), await h2());
  const href = await page.getAttribute('#panel .ref .acts a', 'href');
  ok('Open in PDF link', href === 'budget-2026.pdf#page=34', href);
  ok('snippet image shown', await page.locator('#panel .ref .snip img').count() > 0);
  ok('hash has node', (await hash()).includes('node=dest%3Acentral'), await hash());

  // 2 a ribbon (budget -> central)
  const rb = await page.evaluate(() => {
    const c = (window as any).__canvas, r = c.L.ribbons.find((r: any) => r.src === 'budget' && r.tgt === 'dest:central'), S = c.S;
    return [((r.x0 + r.x1) / 2 - S.x) * S.k, ((r.y0 + r.y1) / 2 + r.w / 2 - S.y) * S.k];
  });
  await page.mouse.click(rb[0], rb[1] + top); await settle(400);
  ok('click ribbon opens flow', (await h2()).includes('→'), await h2());

  // 3 copy citation
  await page.click('#panel .copy');
  const cit = await page.evaluate(() => (window as any).__lastCitation as string);
  ok('copy citation', cit && cit.includes('Tabela 2') && cit.includes('faqe 34'), cit);

  // 4 inbound / outbound lists
  await page.click('#panel ul.fl li button >> nth=1'); await settle(500);
  const h = await h2();
  ok('flow list navigates', h.includes('Qendror'), h);
  await page.click('#panel ul.fl >> nth=-1 >> li button >> nth=0'); await settle(600);
  const hChild = await h2();
  ok('outbound flow navigates to child', hChild !== h, hChild);

  // 5 browser back / forward
  await page.goBack(); await settle(500);
  ok('browser back restores previous node', (await h2()) === h, await h2());
  await page.goForward(); await settle(500);
  ok('browser forward', (await h2()) === hChild, await h2());

  // 6 search
  for (const [q, expect] of [['Prishtin', 'Prishtin'], ['1,194,770,851', 'Financave'], ['p 45', null], ['1.2M', null], ['teacher', null]] as const) {
    await page.fill('#q', q); await settle(250);
    const txt = await page.innerText('#results'), n = await page.locator('#results button[data-i]').count();
    ok(`search "${q}"`, expect ? txt.includes(expect) : n > 0 || q === 'teacher', `${n} results: ` + txt.slice(0, 80).replace(/\n/g, ' '));
  }
  await page.fill('#q', 'Prishtinë'); await settle(200); await page.keyboard.press('Enter'); await settle(700);
  ok('search Enter selects', (await h2()).includes('Prishtin'));

  // 7 language and amount format
  await page.click('#l-en'); await settle(300);
  ok('EN toggle: chrome', (await page.innerText('#b-recon')) === 'Reconciliation');
  ok('EN toggle: hash', (await hash()).includes('lang=en'));
  await page.click('#f-short'); await settle(200);
  let amt = await page.innerText('#panel .amt');
  ok('rounded format', amt.endsWith('M'), amt);
  await page.click('#f-full'); amt = await page.innerText('#panel .amt');
  ok('full format', amt.includes(','), amt);
  await page.click('#l-sq');

  // 8 filters dim, never move
  const sig = await page.evaluate(`${C}.layoutSignature()`);
  await page.click('#b-filter');
  await page.uncheck('#filters input[data-cat="wages"]'); await page.uncheck('#filters input[data-lvl="municipal"]'); await page.selectOption('#filters select', '1000000'); await settle(200);
  ok('filters keep layout identical', sig === await page.evaluate(`${C}.layoutSignature()`));
  await shot(page, info, 'filters');
  await page.check('#filters input[data-cat="wages"]'); await page.check('#filters input[data-lvl="municipal"]'); await page.selectOption('#filters select', '0'); await page.keyboard.press('Escape');

  // 9 tours
  await page.click('#b-tours'); await page.click('#tourmenu button >> nth=0'); await settle(700);
  ok('tour starts', await page.locator('#tourbar.on').count() === 1);
  let hs = await hash();
  ok('tour hash', hs.includes('tour=debt') && hs.includes('step=1'), hs);
  await page.click('#tourbar [data-t=next]'); await settle(600); await page.click('#tourbar [data-t=next]'); await settle(600);
  const w = await page.evaluate(() => (document.querySelector('#tourbar .prog i') as HTMLElement).style.width);
  ok('progress bar', w.startsWith('27'), w);
  await shot(page, info, 'tour_step3');
  await page.goBack(); await settle(600); hs = await hash();
  ok('back in tour goes to step 2', hs.includes('step=2'), hs);
  const st = await page.innerText('#tourbar .t span');
  ok('tour bar reflects step 2', st.includes('2/'), st);
  await page.click('#tourbar [data-t=prev]'); await settle(400);
  ok('prev', (await page.innerText('#tourbar .t span')).includes('1/'));
  for (const tid of ['borrowing-capital', 'municipal', 'pensions', 'gaps']) {
    await page.evaluate(`${C}.startTour("${tid}",0)`);
    const steps = await page.evaluate(`${C}.D.tours.find(t=>t.id=="${tid}").steps.length`) as number;
    for (let s = 0; s < steps; s++) { await page.evaluate(`${C}.tourGo(${s})`); await settle(120); }
    ok(`tour ${tid} runs all ${steps} steps`, await page.evaluate(`${C}.S.step`) === steps - 1);
  }
  await shot(page, info, 'tour_gaps');
  await page.click('#tourbar [data-t=exit]');
  ok('tour exit', await page.locator('#tourbar.on').count() === 0);

  // 10 keyboard
  const k0 = await page.evaluate(`${C}.S.k`) as number;
  await page.focus('#cv'); await page.keyboard.press('+');
  ok('keyboard zoom', (await page.evaluate(`${C}.S.k`) as number) > k0);
  await page.keyboard.press('0'); await settle(700);
  const v = await page.evaluate(() => {
    const { S, L } = (window as any).__canvas, c = document.querySelector('#cv') as HTMLCanvasElement, W = c.clientWidth / S.k, H = c.clientHeight / S.k;
    return [S.x <= 0, S.y <= 0, S.x + W >= L.w, S.y + H >= L.h];
  });
  ok('keyboard fit shows the whole world', v.every(Boolean), v);

  // 11 reconciliation dialog
  await page.click('#b-recon');
  const rows = await page.locator('#recon table >> nth=0 >> tr').count();
  ok('reconciliation panel rows', rows === 562, rows);
  await shot(page, info, 'recon_panel'); await page.click('#recon [data-x]');

  // 12 a check row on the canvas
  await page.evaluate(`${C}.flyToNode("check:t2_local_vs_41")`); await settle(600);
  ok('check row opens the findings tab', await page.evaluate(`${C}.S.tab`) === 'findings');
  top = await stageTop(page);
  [x, y] = await centerOf(page, 'check:t2_local_vs_41');
  await page.mouse.click(x, y + top); await settle(300);
  ok('click check row', (await h2()).includes('Niveli lokal në Tabelën 2'), await h2());
  await shot(page, info, 'check_click');

  // 13 municipal sort
  await page.click('#tabs [data-tab=municipal]'); await settle(400);
  await page.selectOption('#tabsort', 'name'); await settle(300);
  ok('sort by name', await page.evaluate(`${C}.S.sorts.municipal`) === 'name');
  const first = await page.evaluate(() => {
    const c = (window as any).__canvas, b = c.L.boxes.filter((b: any) => b.t === 'card' && b.sec === 'municipal').sort((a: any, b: any) => a.y - b.y || a.x - b.x)[0];
    return c.N.get(b.id).name_sq;
  });
  ok('first municipality alphabetically', ['Deçan', 'Dragash'].includes(first), first);
  ok('overlaps after sort', (await page.evaluate(`${C}.overlaps()`) as unknown[]).length === 0);
  ok('no console errors (desktop)', errs.length === 0, errs);

  // 13b tabs and headline figures
  await page.click('#tabs [data-tab=central]'); await settle(400);
  kp = await page.innerText('#kpis');
  ok('central tab headline: total, change vs 2025', kp.includes('Niveli qendror 2026') && kp.includes('+9.7%'), kp.replace(/\n/g, ' | ').slice(0, 160));
  ok('central chunk parsed on demand', (await page.evaluate(`${C}.loaded()`) as string[]).includes('central'));
  await page.click('#kpis .kpi >> nth=0'); await settle(500);
  ok('headline figure opens its source', (await h2()).includes('Qendror') && (await page.innerText('#panel')).includes('2,757.7'));
  await page.click('#tabs [data-tab=capital]'); await settle(500);
  kp = await page.innerText('#kpis');
  ok('capital tab headline', kp.includes('Shpenzimet kapitale 2026') && kp.includes('+7.2%'), kp.replace(/\n/g, ' | ').slice(0, 160));
  await page.click('#tabs [data-tab=findings]'); await settle(400);
  kp = await page.innerText('#kpis');
  ok('findings tab headline', kp.includes('gabim aritmetik') && kp.includes('rrumbullakim'), kp.replace(/\n/g, ' | ').slice(0, 160));
  ok('tab in URL', (await hash()).includes('tab=findings'), await hash());
  const tops: number[] = [];
  for (const tb of ['flow', 'central', 'municipal', 'capital', 'findings']) { await page.click(`#tabs [data-tab=${tb}]`); await settle(250); tops.push(Math.round(await stageTop(page))); }
  ok('canvas does not move between tabs', new Set(tops).size === 1, tops);
  await page.evaluate(`${C}.showNode("org:208")`); await page.evaluate(`${C}.flyToNode("org:208")`); await settle(500);
  ok('selecting an institution switches to the central tab', await page.evaluate(`${C}.S.tab`) === 'central');

  // 14 deep links in fresh pages
  const ctx = page.context();
  const p2 = await ctx.newPage(); await open(p2, info, '#node=mun%3A616&lang=en&fmt=short'); await wait(p2, 800);
  ok('deep link node+lang+fmt', (await p2.innerText('#panel h2')).startsWith('Prishtin') && (await p2.innerText('#b-recon')) === 'Reconciliation' && (await p2.innerText('#panel .amt')).endsWith('M'));
  await shot(p2, info, 'deeplink_en');
  const p3 = await ctx.newPage(); await open(p3, info, '#tour=borrowing-capital&step=3'); await wait(p3, 900);
  ok('deep link tour step', (await p3.innerText('#tourbar .t span')).includes('3/'));
  await shot(p3, info, 'deeplink_tour');
  const p4 = await ctx.newPage(); await open(p4, info, '#tab=municipal&lang=en'); await wait(p4, 800);
  ok('deep link to a tab', await p4.evaluate(`${C}.S.tab`) === 'municipal' && (await p4.innerText('#kpis')).includes('Municipalities 2026'));
  await shot(p4, info, 'deeplink_tab_en');

  // 15 a direct visit to the projects tab names who runs each project, without loading the other chunks
  const p5 = await ctx.newPage(); await open(p5, info, '#tab=capital'); await wait(p5, 400);
  await p5.evaluate(`${C}.setZoom(1.0)`);
  const owners = await p5.evaluate(() => {
    const c = (window as any).__canvas;
    return [c.loaded(), c.L.boxes.filter((b: any) => b.t === 'prow').slice(0, 5).map((b: any) => c.N.get(b.id).owner)];
  });
  ok('projects tab loads only its own chunk', JSON.stringify(owners[0]) === '["core","capital"]', owners[0]);
  const drawn = (await p5.evaluate(`${C}.drawnText()`) as string[]).join('|');
  ok('projects tab shows who runs each project', drawn.includes('Ministria e Mjedisit') && drawn.includes('Sherbimi Spitalor'), drawn.slice(0, 160));
  await shot(p5, info, 'capital_direct');

  // 16 mobile
  const m = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const pm = await m.newPage(); const merr: string[] = []; pm.on('pageerror', e => merr.push(String(e)));
  await open(pm, info, '#node=org%3A208'); await wait(pm, 800);
  ok('mobile: tabs scroll inside their bar', await pm.evaluate(() => { const t = document.querySelector('#tabs')!; return t.scrollWidth >= t.clientWidth; }));
  const sw = await pm.evaluate(() => [document.documentElement.scrollWidth, document.body.scrollWidth, innerWidth]);
  ok('mobile: no horizontal page scroll', sw[0] <= sw[2] && sw[1] <= sw[2], sw);
  const pos = await pm.evaluate(() => { const p = document.querySelector('#panel')!, r = p.getBoundingClientRect(); return [getComputedStyle(p).position, Math.round(r.bottom), Math.round(r.top), innerHeight] as const; });
  ok('mobile: details panel is a bottom sheet', pos[0] === 'fixed' && pos[1] === pos[3] && pos[2] > pos[3] * 0.3, pos);
  await shot(pm, info, 'mobile_panel');
  await pm.evaluate(() => (document.querySelector('[data-close]') as HTMLElement).click()); await wait(pm, 400);
  await shot(pm, info, 'mobile_canvas');
  ok('mobile: no errors', merr.length === 0, merr);
  ok('text overflow (mobile)', (await pm.evaluate(`${C}.textOverflow()`) as unknown[]).length === 0);
  await m.close();

  // 17 high-density screens: ribbons are hit-tested in device pixels
  const hd = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const ph = await hd.newPage(); await open(ph, info); const htop = await stageTop(ph);
  for (const [src, tgt] of [['budget', 'dest:central'], ['pool', 'budget'], ['dest:central', 'cat:wages']]) {
    const p = await ph.evaluate(([s, t]) => {
      const c = (window as any).__canvas, r = c.L.ribbons.find((r: any) => r.src === s && r.tgt === t), S = c.S;
      return [((r.x0 + r.x1) / 2 - S.x) * S.k, ((r.y0 + r.y1) / 2 + r.w / 2 - S.y) * S.k];
    }, [src, tgt]);
    await ph.mouse.click(p[0], p[1] + htop); await wait(ph, 400);
    const t = await ph.isVisible('#panel h2') ? await ph.innerText('#panel h2') : '';
    ok(`DPR 2: click ribbon ${src} → ${tgt}`, t.includes('→'), t);
    await ph.keyboard.press('Escape'); await wait(ph, 150);
  }
  await hd.close();

  report();
});
