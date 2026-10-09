import { flushSync } from 'react-dom';
import { Engine, type Hit, type Insets } from './canvas/engine';
import { Worlds } from './canvas/worlds';
import { citeFlow, citeNode, copyText } from './cite';
import { cfg, firstTab, tabIds, tabs } from './config';
import type { Graph } from './data/graph';
import type { AmountFormat } from './format';
import { docTitle, str } from './i18n';
import { selectedFlow, selectedId, viewOf } from './state/selection';
import { ui, type PanelView, type UIState } from './state/store';
import { currentHash, memStep, probeHistory, writeHash } from './state/url';
import type { BudgetNode, Check, Finding, Kpi, ReconFilter, Tour } from './types';

/** What a headline figure opens. */
export type HeadlineTarget = { kind: 'recon'; filter: ReconFilter } | { kind: 'check'; check: Check } | { kind: 'kpi'; kpi: Kpi };

/** Every user action, and the only writer of UI state. Owns the canvas engine and the tab worlds, and keeps the URL in sync. */
export class Controller {
  readonly engine: Engine;
  readonly worlds: Worlds;
  private applying = 0;
  private busy = new Set<Promise<unknown>>();
  private toastTimer = 0;

  constructor(readonly g: Graph) {
    this.worlds = new Worlds(g, tab => this.s.sorts[tab]);
    this.engine = new Engine(g, {
      view: () => viewOf(this.s, g),
      onClick: h => this.onCanvasClick(h),
      onLevel: level => this.commit({ level }),
    }, tabs()[0]);
    ui().subscribe(() => this.engine.invalidate());
  }

  private get s(): UIState { return ui().get(); }

  /** Commits synchronously: the camera code measures the tour bar right after a step, and tests read the DOM right after an action. */
  private commit(patch: Partial<UIState>) { flushSync(() => ui().set(patch)); }

  /** Runs an action that may wait for data, so that idle() can wait for it. */
  private run<T>(action: () => Promise<T>): Promise<T> {
    const p = action();
    this.busy.add(p);
    p.finally(() => this.busy.delete(p)).catch(() => {});
    return p;
  }

  /** Resolves once every action started so far has finished and React has committed. */
  async idle() {
    while (this.busy.size) await Promise.allSettled([...this.busy]);
    flushSync(() => {});
  }

  // ---- the details panel, which is also the selection ----
  private open(panel: PanelView) {
    this.commit({ panel, panelSeq: this.s.panelSeq + 1 });
    requestAnimationFrame(() => this.engine.resize());
  }

  closePanel() {
    this.commit({ panel: null });
    requestAnimationFrame(() => this.engine.resize());
  }

  showNode(id: string, push = true) {
    return this.run(async () => {
      await this.g.ensure(id);
      if (!this.g.N.has(id)) return;
      this.open({ type: 'node', id });
      if (push) this.setHash();
    });
  }

  showFlow(fid: string, push = true) {
    return this.run(async () => {
      await this.g.ensureFlow(fid);
      const f = this.g.F.get(fid);
      if (!f) return;
      await Promise.all([this.g.ensure(f.source), this.g.ensure(f.target)]);
      this.open({ type: 'flow', id: fid });
      if (push) this.setHash();
    });
  }

  showCheck(check: Check) { this.open({ type: 'check', check }); }
  showFinding(finding: Finding, idx: number) { this.open({ type: 'finding', finding, idx }); }

  /** Select a node and bring it on screen, switching tab if needed. */
  go(id: string) { return this.run(async () => { await this.showNode(id); await this.flyToNode(id); }); }
  goFlow(fid: string) { return this.run(async () => { await this.showFlow(fid); await this.flyToFlow(fid); }); }

  openHeadline(t: HeadlineTarget) {
    if (t.kind === 'recon') this.openRecon(t.filter);
    else if (t.kind === 'check') { this.showCheck(t.check); this.flyToNode('check:' + t.check.id); }
    else if (t.kpi.node) this.go(t.kpi.node);
    else this.open({ type: 'kpi', kpi: t.kpi });
  }

  onCanvasClick(h: Hit | null) {
    if (!h) { if (!this.s.tour) this.closePanel(); this.setHash(); return; }
    if (h.kind === 'node') this.showNode(h.id);
    else if (h.kind === 'flow') this.showFlow(h.id);
    else if (h.kind === 'check') this.showCheck(h.check);
    else if (h.kind === 'finding') this.showFinding(h.finding, h.idx);
  }

  // ---- camera and tabs ----
  /** The camera keeps clear of the tour bar, and of the bottom-sheet panel on phones. */
  private insets(): Insets {
    return { top: this.s.tour ? (document.getElementById('tourbar')?.offsetHeight || 0) + 20 : 0, sheet: this.s.panel !== null };
  }

  flyToNode(id: string, maxK?: number) {
    return this.run(async () => {
      const tb = await this.worlds.tabFor(id, this.s.tab);
      if (tb !== this.s.tab) await this.switchTab(tb, { keepCam: true, noHash: true });
      const b = this.worlds.boxIn(this.engine.L, id, false);
      if (b) this.engine.flyToBox(b, !!this.g.N.get(id)?.anchor, this.insets(), maxK);
    });
  }

  flyToFlow(fid: string) {
    return this.run(async () => {
      await this.g.ensureFlow(fid);
      const f = this.g.F.get(fid);
      if (!f) return;
      if (!this.engine.L.ribbons.some(r => r.id === fid)) {
        const tb = await this.worlds.tabForRibbon(fid);
        if (tb) await this.switchTab(tb, { keepCam: true, noHash: true });
      }
      // a flow out of a destination is shown at its target (the destination itself is on the overview)
      if (!this.engine.flyToRibbon(fid)) await this.flyToNode(this.g.N.get(f.source)?.kind === 'dest' ? f.target : f.source);
    });
  }

  async switchTab(tab: string, { keepCam = false, noHash = false } = {}) {
    if (!tabIds().includes(tab)) tab = firstTab();
    const fresh = !this.worlds.get(tab);
    if (fresh) this.commit({ loading: true });
    try {
      this.engine.show(await this.worlds.prepare(tab), keepCam);
      this.commit({ tab });
    } finally {
      if (fresh) this.commit({ loading: false });
    }
    if (!noHash) this.setHash();
  }

  /** A click on a tab: a selection that lives on another tab is closed, so the URL always describes what is on screen. */
  pickTab(tab: string) {
    return this.run(async () => {
      if (this.s.tour) this.exitTour();
      const sel = selectedId(this.s), L = this.worlds.get(tab);
      if ((sel || selectedFlow(this.s)) && !(sel && L && this.worlds.boxIn(L, sel, true))) this.closePanel();
      await this.switchTab(tab);
    });
  }

  setSort(tab: string, v: string) {
    this.commit({ sorts: { ...this.s.sorts, [tab]: v } });
    this.worlds.invalidate(tab);
    if (this.s.tab === tab) this.run(async () => { this.engine.show(await this.worlds.prepare(tab), true); this.engine.fitTab(); });
  }

  // ---- tours ----
  startTour(id: string, step: number, push = true) {
    const tr = this.g.D.tours.find(x => x.id === id);
    return tr ? this.showStep(tr, step, push) : Promise.resolve();
  }

  tourGo(i: number, push = true) {
    return this.s.tour ? this.showStep(this.s.tour, i, push) : Promise.resolve();
  }

  /** Load every node and flow the tour has visited, then show the step: tour, step and panel change together. */
  private showStep(tr: Tour, i: number, push: boolean) {
    return this.run(async () => {
      i = Math.max(0, Math.min(tr.steps.length - 1, i));
      const st = tr.steps[i];
      await Promise.all(tr.steps.slice(0, i + 1).flatMap(s => [this.g.ensure(s.node), s.flow ? this.g.ensureFlow(s.flow) : null]));
      this.commit({ tour: tr, step: i, panel: { type: 'node', id: st.node }, panelSeq: this.s.panelSeq + 1 });
      requestAnimationFrame(() => { this.engine.resize(); this.flyToNode(st.node); });
      if (push) this.setHash();
    });
  }

  exitTour() {
    this.commit({ tour: null });
    this.setHash();
  }

  // ---- chrome ----
  private setLangFmt(lang: string, fmt: AmountFormat) {
    this.engine.clearTextCache();
    document.documentElement.lang = lang;
    document.title = docTitle(lang);
    this.commit({ lang, fmt });
  }

  setLang(l: string) { if (cfg().langs.includes(l)) { this.setLangFmt(l, this.s.fmt); this.setHash(true); } }
  setFmt(f: AmountFormat) { this.setLangFmt(this.s.lang, f); this.setHash(true); }

  toggleMenu(m: 'filters' | 'tours') { this.commit({ menu: this.s.menu === m ? null : m }); }
  closeMenus() { if (this.s.menu) this.commit({ menu: null }); }

  openRecon(flt: ReconFilter | null = this.s.clsFilter) { this.commit({ recon: true, clsFilter: flt }); }
  closeRecon() { this.commit({ recon: false }); }
  setClsFilter(flt: ReconFilter | null) { this.commit({ clsFilter: flt }); }

  toggleCat(c: string, on: boolean) {
    const cats = new Set(this.s.filt.cats);
    if (on) cats.add(c); else cats.delete(c);
    this.commit({ filt: { ...this.s.filt, cats } });
  }
  toggleLevel(id: string, on: boolean) { this.commit({ filt: { ...this.s.filt, levels: { ...this.s.filt.levels, [id]: on } } }); }
  setMin(min: number) { this.commit({ filt: { ...this.s.filt, min } }); }

  cite(n: BudgetNode) { this.copy(citeNode(n, this.g, this.s.lang)); }
  citeFlow(fid: string) { const f = this.g.F.get(fid); if (f) this.copy(citeFlow(f, this.g, this.s.lang)); }

  private copy(text: string) {
    (window as unknown as { __lastCitation: string }).__lastCitation = text;
    copyText(text).then(() => this.toast(str(this.s.lang, 'copied')));
  }

  private toast(msg: string) {
    this.commit({ toast: { msg, seq: (this.s.toast?.seq ?? 0) + 1 } });
    clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => this.commit({ toast: null }), 1600);
  }

  // ---- URL ----
  setHash(replace?: boolean) {
    if (this.applying) return;
    const s = this.s, p = new URLSearchParams(), sel = selectedId(s), node = sel && this.g.N.has(sel) ? sel : null, flow = selectedFlow(s);
    if (node) p.set('node', node);
    if (flow && !s.tour) p.set('flow', flow);
    if (s.tour) { p.set('tour', s.tour.id); p.set('step', String(s.step + 1)); }
    if (s.tab !== firstTab() && !node && !s.tour) p.set('tab', s.tab);
    if (s.lang !== cfg().langs[0]) p.set('lang', s.lang);
    if (s.fmt !== 'full') p.set('fmt', s.fmt);
    const h = '#' + p.toString(), cur = currentHash();
    if (h === cur || (h === '#' && !cur)) return;
    writeHash(h, replace);
  }

  applyHash(first: boolean) {
    return this.run(async () => {
      this.applying++;
      try {
        const p = new URLSearchParams(currentHash().slice(1));
        const l = p.get('lang'), lang = l && cfg().langs.includes(l) ? l : cfg().langs[0], fmt: AmountFormat = p.get('fmt') === 'short' ? 'short' : 'full';
        if (lang !== this.s.lang || fmt !== this.s.fmt) this.setLangFmt(lang, fmt);
        const tour = p.get('tour');
        if (tour) { await this.startTour(tour, (+(p.get('step') ?? 1) || 1) - 1, false); return; }
        if (this.s.tour) this.commit({ tour: null });
        const nid = p.get('node'), fl = p.get('flow');
        await Promise.all([nid && this.g.ensure(nid), fl && this.g.ensureFlow(fl)]);
        if (nid && this.g.N.has(nid)) { await this.showNode(nid, false); await this.flyToNode(nid); }
        else if (fl && this.g.F.has(fl)) { await this.showFlow(fl, false); await this.flyToFlow(fl); }
        else {
          await this.switchTab(p.get('tab') ?? firstTab(), { noHash: true });
          if (!first) this.closePanel();
        }
      } finally {
        this.applying--;
        this.engine.invalidate();
      }
    });
  }

  memNav(d: number) { if (memStep(d)) this.applyHash(false); }

  // ---- keyboard ----
  onKey = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    if (target.matches('input,textarea,select')) { if (e.key === 'Escape') target.blur(); return; }
    const k = e.key, E = this.engine, s = this.s;
    if (k === '+' || k === '=') E.zoomCenter(1.4);
    else if (k === '-' || k === '_') E.zoomCenter(1 / 1.4);
    else if (k === '0' || k === 'f' || k === 'F') E.fitAll();
    else if (s.hist.memory && e.altKey && (k === 'ArrowLeft' || k === 'ArrowRight')) this.memNav(k === 'ArrowLeft' ? -1 : 1);
    else if (k === 'ArrowLeft') E.pan(-80, 0);
    else if (k === 'ArrowRight') E.pan(80, 0);
    else if (k === 'ArrowUp') E.pan(0, -80);
    else if (k === 'ArrowDown') E.pan(0, 80);
    else if (k === '/') document.getElementById('q')?.focus();
    else if (k === 'Escape') { if (s.tour) this.exitTour(); else this.closePanel(); this.closeMenus(); this.setHash(); }
    else if (s.tour && (k === 'n' || k === 'N' || k === 'PageDown')) this.tourGo(s.step + 1);
    else if (s.tour && (k === 'p' || k === 'P' || k === 'PageUp')) this.tourGo(s.step - 1);
    else if (k === 'l' || k === 'L') { const L = cfg().langs; this.setLang(L[(L.indexOf(s.lang) + 1) % L.length]); }
    else if (k === 'r' || k === 'R') this.setFmt(s.fmt === 'full' ? 'short' : 'full');
    else return;
    e.preventDefault();
  };

  // ---- start ----
  async boot(cv: HTMLCanvasElement, stage: HTMLElement) {
    probeHistory();
    this.engine.attach(cv, stage);
    this.engine.resize();
    this.engine.show(await this.worlds.prepare(firstTab()));
    document.addEventListener('keydown', this.onKey);
    document.addEventListener('click', e => { if (!(e.target as HTMLElement).closest('#filters,#b-filter,#tourmenu,#b-tours')) this.closeMenus(); });
    const onNav = () => { if (!this.s.hist.memory) this.applyHash(false); };
    window.addEventListener('popstate', onNav);
    window.addEventListener('hashchange', onNav);
    await this.applyHash(true);
    this.g.PERF.ready = Math.round(performance.now() - (this.g.PERF.start ?? 0));
  }
}
