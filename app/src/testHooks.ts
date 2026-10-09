import type { Controller } from './controller';
import type { AmountFormat } from './format';
import { ui } from './state/store';

/** window.__canvas: what the browser tests drive and measure. Actions return promises that settle once the DOM is updated. */
export function installTestHooks(c: Controller) {
  const { g, engine: E, worlds } = c;
  const settled = <A extends unknown[]>(f: (...a: A) => unknown) => async (...a: A) => { await f(...a); await c.idle(); };
  const hooks = {
    get S() { return { ...ui().get(), ...E.cam }; },
    get L() { return E.L; },
    N: g.N, F: g.F, D: g.D, PERF: g.PERF, LAYOUTS: worlds.built,
    loaded: () => [...g.LOADED],
    ensure: (id: string) => g.ensure(id),
    idle: () => c.idle(),
    switchTab: settled((tab: string) => c.switchTab(tab)),
    showNode: settled((id: string) => c.showNode(id)),
    showFlow: settled((id: string) => c.showFlow(id)),
    flyToNode: settled((id: string) => c.flyToNode(id)),
    startTour: settled((id: string, step: number) => c.startTour(id, step)),
    tourGo: settled((i: number) => c.tourGo(i)),
    exitTour: () => c.exitTour(),
    setLang: (l: string) => c.setLang(l),
    setFmt: (f: AmountFormat) => c.setFmt(f),
    overlaps: () => E.overlaps(),
    textOverflow: () => E.textOverflow(),
    drawnText: () => E.drawnText(),
    layoutSignature: () => E.layoutSignature(),
    setZoom: (k: number) => { E.setZoom(k); E.draw(); },
    setCamera: (cam: { k?: number; x?: number; y?: number }) => { Object.assign(E.cam, cam); E.draw(); },
    fitAll: () => { E.fitAll(0); E.draw(); },
    fitOverview: () => { E.fitTab(); E.draw(); },
    hit: (x: number, y: number) => E.hit(x, y),
    draw: () => E.draw(),
    level: () => E.level(),
    screenOf: (id: string) => E.screenOf(id),
  };
  (window as unknown as { __canvas: typeof hooks }).__canvas = hooks;
}
