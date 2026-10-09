import type { Graph } from '../data/graph';
import type { View } from '../state/selection';
import type { Check, Finding } from '../types';
import { emptyLayout, type Box, type BoxOf, type Layout } from './layout';
import { categoryColors, ribbonPath, Renderer, toScreen, type Camera } from './render';

export type Hit =
  | { kind: 'node'; id: string }
  | { kind: 'flow'; id: string }
  | { kind: 'check'; check: Check }
  | { kind: 'finding'; finding: Finding; idx: number }
  /** a box that takes the click but does nothing (it must not count as a click on empty space) */
  | { kind: 'inert' };

/** Space the camera keeps clear when it flies to something: the tour bar on top, the bottom-sheet panel on phones. */
export interface Insets { top: number; sheet: boolean }

export interface EngineHooks {
  view: () => View;
  onClick: (h: Hit | null) => void;
  onLevel: (level: number) => void;
}

/** Semantic zoom: below 0.55 totals only, below 1.3 organisations by category, otherwise everything. */
export const levelOf = (k: number) => (k < 0.55 ? 0 : k < 1.3 ? 1 : 2);
const clampK = (k: number) => Math.max(0.02, Math.min(8, k));
const CLICKABLE = new Set<Box['t']>(['snode', 'card', 'row', 'prow', 'check', 'finding', 'prest']);

/** The canvas: one world (a tab's layout) at a time, a camera over it, the draw loop, pointer input and hit testing. */
export class Engine {
  cam: Camera = { k: 0.2, x: 0, y: 0 };
  L: Layout;
  VW = 0;
  VH = 0;
  private cams: Record<string, Camera> = {};
  private renderer!: Renderer;
  private cv!: HTMLCanvasElement;
  private cx!: CanvasRenderingContext2D;
  private stage!: HTMLElement;
  private DPR = 1;
  private dirty = true;
  private anim = 0;
  private reportedLevel = -1;

  constructor(private g: Graph, private hooks: EngineHooks, firstTab: Layout['tab']) {
    this.L = emptyLayout(firstTab);
  }

  attach(cv: HTMLCanvasElement, stage: HTMLElement) {
    this.cv = cv; this.stage = stage; this.cx = cv.getContext('2d')!;
    const css = getComputedStyle(document.documentElement);
    this.renderer = new Renderer(this.cx, this.g, css.getPropertyValue('--sans'), categoryColors(css));
    this.pointer();
    new ResizeObserver(() => this.resize()).observe(stage);
    const loop = () => { if (this.dirty) this.draw(); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  }

  invalidate() { this.dirty = true; }
  clearTextCache() { this.renderer.clearTextCache(); this.dirty = true; }

  resize() {
    this.DPR = Math.min(window.devicePixelRatio || 1, 2);
    this.VW = this.stage.clientWidth; this.VH = this.stage.clientHeight;
    this.cv.width = Math.round(this.VW * this.DPR); this.cv.height = Math.round(this.VH * this.DPR);
    this.dirty = true;
  }

  /** Show a world. Each tab keeps its own camera; the first time a tab is shown it is fitted, unless `keepCam`. */
  show(L: Layout, keepCam = false) {
    const from = this.L.tab.id, to = L.tab.id;
    if (to !== from) { this.cams[from] = { ...this.cam }; cancelAnimationFrame(this.anim); }
    this.L = L;
    if (!keepCam) { if (this.cams[to]) Object.assign(this.cam, this.cams[to]); else this.fitTab(); }
    this.dirty = true;
  }

  // ---- camera ----
  zoomAt(f: number, sx: number, sy: number) {
    cancelAnimationFrame(this.anim);
    const c = this.cam, wx = sx / c.k + c.x, wy = sy / c.k + c.y;
    c.k = clampK(c.k * f); c.x = wx - sx / c.k; c.y = wy - sy / c.k;
    this.dirty = true;
  }

  zoomCenter(f: number) { this.zoomAt(f, this.VW / 2, this.VH / 2); }

  pan(dx: number, dy: number) { cancelAnimationFrame(this.anim); this.cam.x += dx / this.cam.k; this.cam.y += dy / this.cam.k; this.dirty = true; }

  setZoom(k: number) {
    const c = this.cam, mid = { x: c.x + this.VW / 2 / c.k, y: c.y + this.VH / 2 / c.k };
    c.k = k; c.x = mid.x - this.VW / 2 / k; c.y = mid.y - this.VH / 2 / k;
    this.dirty = true;
  }

  private fitBox(x: number, y: number, w: number, h: number, pad = 40, maxK = 3): Camera {
    const k = clampK(Math.min((this.VW - 2 * pad) / w, (this.VH - 2 * pad) / h, maxK));
    return { k, x: x + w / 2 - this.VW / 2 / k, y: y + h / 2 - this.VH / 2 / k };
  }

  private flyTo(target: Camera, ms = 450) {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) ms = 0;
    const c = this.cam, a = { ...c }, t0 = performance.now();
    cancelAnimationFrame(this.anim);
    const step = (now: number) => {
      const u = ms ? Math.min(1, (now - t0) / ms) : 1, e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      c.k = Math.exp(Math.log(a.k) + (Math.log(target.k) - Math.log(a.k)) * e);
      // interpolate the screen centre, not the corner, so the motion stays smooth while zooming
      const ca = { x: a.x + this.VW / 2 / a.k, y: a.y + this.VH / 2 / a.k }, cb = { x: target.x + this.VW / 2 / target.k, y: target.y + this.VH / 2 / target.k };
      c.x = ca.x + (cb.x - ca.x) * e - this.VW / 2 / c.k;
      c.y = ca.y + (cb.y - ca.y) * e - this.VH / 2 / c.k;
      this.dirty = true;
      if (u < 1) this.anim = requestAnimationFrame(step);
    };
    this.anim = requestAnimationFrame(step);
  }

  fitAll(ms?: number) {
    const b = this.fitBox(-20, -20, this.L.w + 40, this.L.h + 40, 10, 10);
    if (ms === 0) Object.assign(this.cam, b); else this.flyTo(b);
    this.dirty = true;
  }

  /** The opening view of a tab: a sankey's bars and labels, the checks list by width, other worlds their top part. */
  fitTab() {
    const L = this.L;
    if (L.tab.layout === 'sankey') {
      const parts = L.boxes.flatMap(q => (q.t === 'snode' ? [q, { x: q.lx, y: q.y, w: q.lw, h: q.h }] : q.id === 'sec:' + L.tab.title ? [q] : []));
      const x0 = Math.min(...parts.map(q => q.x)), x1 = Math.max(...parts.map(q => q.x + q.w));
      const y0 = Math.min(...parts.map(q => q.y)), y1 = Math.max(...parts.map(q => q.y + q.h));
      Object.assign(this.cam, this.fitBox(x0, y0, x1 - x0, y1 - y0 + 60, 16, 2));
    } else if (L.tab.layout === 'checks') Object.assign(this.cam, { k: clampK((this.VW - 24) / (L.w + 40)), x: -20, y: -20 });
    else Object.assign(this.cam, this.fitBox(-20, -20, L.w + 40, Math.min(L.h, L.w * 0.7) + 40, 12, 1));
    this.dirty = true;
  }

  /** Fly to a box: a sankey bar with its label, a row within its card, a card's top, or an anchored node's surroundings. */
  flyToBox(b: Box, anchored: boolean, insets: Insets, maxK?: number) {
    let { x, y, w, h } = b;
    if (b.t === 'snode') { x = Math.min(b.x, b.lx) - 40; w = Math.max(b.x + b.w, b.lx + b.lw) - x + 40; y -= 120; h += 240; }
    if (b.t === 'row' || b.t === 'prow') { const c = (b.t === 'row' && this.L.byId.get(b.card)) || b; x = c.x; w = c.w; y = b.y - 220; h = 440; }
    if (b.t === 'card') h = Math.min(h, 900);
    const mk = anchored ? 0.42 : b.t === 'card' ? 1.25 : b.t === 'snode' ? 1.0 : 2.4;
    if (anchored) { x -= 900; w += 1800; y -= 500; h += 1000; }
    const VW = this.VW, VH = this.VH, pad = VW < 760 ? 16 : 60;
    const availH = (VW < 760 && insets.sheet ? VH * 0.36 : VH) - insets.top;
    const k = clampK(Math.min((VW - 2 * pad) / w, (availH - 2 * pad) / h, maxK || mk));
    this.flyTo({ k, x: x + w / 2 - VW / 2 / k, y: y + h / 2 - availH / 2 / k - insets.top / k });
  }

  flyToRibbon(fid: string) {
    const r = this.L.ribbons.find(r => r.id === fid);
    if (!r) return false;
    const x = Math.min(r.x0, r.x1) - 200, y = Math.min(r.y0, r.y1) - 200, w = Math.abs(r.x1 - r.x0) + 400, h = Math.abs(r.y1 - r.y0) + r.w + 400;
    const k = clampK(Math.min(this.VW / w, this.VH / h, 1.2));
    this.flyTo({ k, x: x + w / 2 - this.VW / 2 / k, y: y + h / 2 - this.VH / 2 / k });
    return true;
  }

  level() { return levelOf(this.cam.k); }

  screenOf(id: string) {
    const b = this.L.byId.get(id);
    if (!b) return null;
    const [x, y] = toScreen(this.cam, b.x, b.y);
    return { x, y, w: b.w * this.cam.k, h: b.h * this.cam.k };
  }

  // ---- hit testing: boxes on top first, then ribbons, then sankey label lanes ----
  hit(sx: number, sy: number): Hit | null {
    const c = this.cam, wx = sx / c.k + c.x, wy = sy / c.k + c.y, lv = this.level(), L = this.L;
    const inside = (b: { x: number; y: number; w: number; h: number }) => wx >= b.x && wx <= b.x + b.w && wy >= b.y && wy <= b.y + b.h;
    for (let i = L.boxes.length - 1; i >= 0; i--) {
      const b = L.boxes[i];
      if (!CLICKABLE.has(b.t) || !inside(b)) continue;
      if (b.t === 'row' && (lv < 1 || (lv < 2 && b.depth > 0))) continue;
      if (b.t === 'card') for (const s of b.segs) if (inside(s) && s.flow) return { kind: 'flow', id: s.flow };
      if (b.t === 'check') return { kind: 'check', check: b.chk };
      if (b.t === 'finding') return { kind: 'finding', finding: b.f, idx: b.idx };
      if (b.t === 'prest') return { kind: 'inert' };
      return { kind: 'node', id: b.id };
    }
    const cx = this.cx;
    for (let i = L.ribbons.length - 1; i >= 0; i--) {
      // paths are in CSS pixels, the canvas bitmap in device pixels: test under the same scale the ribbons are drawn with
      cx.save(); cx.setTransform(this.DPR, 0, 0, this.DPR, 0, 0);
      const on = cx.isPointInPath(ribbonPath(L.ribbons[i], c), sx * this.DPR, sy * this.DPR);
      cx.restore();
      if (on) return { kind: 'flow', id: L.ribbons[i].id };
    }
    for (const b of L.boxes) if (b.t === 'snode' && wx >= b.lx && wx <= b.lx + b.lw && wy >= b.y && wy <= b.y + b.h) return { kind: 'node', id: b.id };
    return null;
  }

  private pointer() {
    const cv = this.cv, ptrs = new Map<number, { x: number; y: number }>();
    let drag: { x: number; y: number; sx: number; sy: number; moved: boolean } | null = null;
    let pinch: { d: number; k: number } | null = null;
    cv.addEventListener('pointerdown', e => {
      cancelAnimationFrame(this.anim); cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
      if (ptrs.size === 1) drag = { x: e.offsetX, y: e.offsetY, sx: this.cam.x, sy: this.cam.y, moved: false };
      if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), k: this.cam.k }; drag = null; }
    });
    cv.addEventListener('pointermove', e => {
      if (!ptrs.has(e.pointerId)) return;
      ptrs.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
      if (pinch && ptrs.size === 2) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
        this.zoomAt((pinch.k * d) / pinch.d / this.cam.k, (a.x + b.x) / 2, (a.y + b.y) / 2);
        return;
      }
      if (drag) {
        const dx = e.offsetX - drag.x, dy = e.offsetY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; cv.classList.add('drag'); }
        if (drag.moved) { this.cam.x = drag.sx - dx / this.cam.k; this.cam.y = drag.sy - dy / this.cam.k; this.dirty = true; }
      }
    });
    const end = (e: PointerEvent) => {
      ptrs.delete(e.pointerId);
      if (ptrs.size < 2) pinch = null;
      if (drag && !drag.moved && e.type === 'pointerup') this.hooks.onClick(this.hit(e.offsetX, e.offsetY));
      if (ptrs.size === 0) { drag = null; cv.classList.remove('drag'); }
    };
    cv.addEventListener('pointerup', end);
    cv.addEventListener('pointercancel', end);
    cv.addEventListener('wheel', e => { e.preventDefault(); this.zoomAt(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015)), e.offsetX, e.offsetY); }, { passive: false });
  }

  draw() {
    this.dirty = false;
    const lv = this.level();
    this.renderer.frame(this.L, this.cam, this.VW, this.VH, this.DPR, this.hooks.view(), lv);
    if (lv !== this.reportedLevel) { this.reportedLevel = lv; this.hooks.onLevel(lv); }
  }

  // ---- verification hooks ----
  textOverflow() {
    const R = this.renderer;
    R.OVERFLOW.length = 0;
    this.draw();
    return R.OVERFLOW.slice(0, 20).concat(R.OVERFLOW.length ? ['count=' + R.OVERFLOW.length] : []);
  }

  drawnText() {
    const R = this.renderer, out: string[] = (R.drawn = []);
    this.draw();
    R.drawn = null;
    return out;
  }

  /** Overlapping boxes (sankey label lanes included), rows outside their card, rows overlapping each other. */
  overlaps() {
    const L = this.L, items: { id: string; x: number; y: number; w: number; h: number }[] = [];
    for (const b of L.boxes) {
      if (b.t === 'row') continue; // rows sit inside their card by design; checked below
      items.push({ id: b.t + ':' + b.id, x: b.x, y: b.y, w: b.w, h: b.h });
      if (b.t === 'snode') items.push({ id: 'label:' + b.id, x: b.lx, y: b.y, w: b.lw, h: b.h });
    }
    const out: string[][] = [];
    const sorted = items.sort((a, b) => a.x - b.x);
    for (let i = 0; i < sorted.length; i++) for (let j = i + 1; j < sorted.length && sorted[j].x < sorted[i].x + sorted[i].w; j++) {
      const a = sorted[i], b = sorted[j];
      if (a.y < b.y + b.h && b.y < a.y + a.h && a.x < b.x + b.w && b.x < a.x + a.w) {
        // a node bar and its own label lane are adjacent by construction
        if (a.id.split(':').slice(1).join(':') === b.id.split(':').slice(1).join(':')) continue;
        out.push([a.id, b.id]);
      }
    }
    const rows = L.boxes.filter((b): b is BoxOf<'row'> => b.t === 'row');
    const byCard = new Map<string, BoxOf<'row'>[]>();
    for (const r of rows) {
      const c = L.byId.get(r.card)!;
      if (!(r.x >= c.x && r.x + r.w <= c.x + c.w && r.y >= c.y && r.y + r.h <= c.y + c.h)) out.push(['row-outside-card', r.id]);
      const a = byCard.get(r.card);
      if (a) a.push(r); else byCard.set(r.card, [r]);
    }
    for (const rs of byCard.values()) { rs.sort((a, b) => a.y - b.y); for (let i = 1; i < rs.length; i++) if (rs[i].y < rs[i - 1].y + rs[i - 1].h) out.push(['row-overlap', rs[i - 1].id, rs[i].id]); }
    return out;
  }

  layoutSignature() {
    return this.L.boxes.map(b => `${b.id}:${b.x.toFixed(1)},${b.y.toFixed(1)},${b.w.toFixed(1)},${b.h.toFixed(1)}`).join('|');
  }
}
