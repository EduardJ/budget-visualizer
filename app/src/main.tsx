import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { levelOf } from './canvas/engine';
import { catIds, cfg, setConfig, tabs } from './config';
import { Controller } from './controller';
import { Graph } from './data/graph';
import { createSource, readConfig } from './data/source';
import { docTitle } from './i18n';
import { createStore } from './state/store';
import { installTestHooks } from './testHooks';
import { App } from './ui/App';
import { RuntimeContext } from './ui/common';
import './styles.css';

async function start() {
  const t0 = performance.now();
  setConfig(readConfig());
  const lang = cfg().langs[0];
  document.documentElement.lang = lang;
  document.title = docTitle(lang);
  const source = createSource();
  const g = new Graph(await source.core(), source);
  g.PERF.start = t0;
  createStore({
    lang, fmt: 'full', tab: tabs()[0].id, tour: null, step: 0,
    filt: { cats: new Set(catIds()), levels: Object.fromEntries((cfg().levels ?? []).map(l => [l.id, true])), min: 0 },
    sorts: Object.fromEntries(tabs().flatMap(t => (t.layout === 'cards' && t.sort ? [[t.id, t.sort[0].id]] : []))),
    clsFilter: null, panel: null, panelSeq: 0, menu: null, recon: false, level: levelOf(0.2), loading: false, toast: null,
    hist: { memory: false, canBack: false, canFwd: false },
  });
  const controller = new Controller(g);
  const root = createRoot(document.getElementById('root')!);
  // rendered synchronously so the canvas exists when the controller boots
  flushSync(() => root.render(<RuntimeContext.Provider value={{ g, c: controller, source }}><App /></RuntimeContext.Provider>));
  installTestHooks(controller);
  await controller.boot(document.getElementById('cv') as HTMLCanvasElement, document.getElementById('stage')!);
}

start().catch(err => {
  console.error(err);
  const el = document.getElementById('root');
  if (!el) return;
  const p = document.createElement('p');
  p.className = 'boot-error';
  p.textContent = `The budget data could not be loaded (${(err && err.message) || err}). Reload the page; if it persists, open an issue.`;
  el.replaceChildren(p);
});
