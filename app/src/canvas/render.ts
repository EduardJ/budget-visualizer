import { catIds, cfg, isNegative, rankingFor } from '../config';
import { clsName, clsOf, CLSCOL, ckv, findingCls, findingDiff } from '../checks';
import type { Graph } from '../data/graph';
import { fmt, nf0, pct } from '../format';
import { loc, str } from '../i18n';
import { passesFilter } from '../state/filters';
import type { View } from '../state/selection';
import type { BudgetNode, Flow, PaletteKey } from '../types';
import { CARD_GAP, rowsFor, type Box, type BoxOf, type Layout, type Ribbon } from './layout';

export const COL = { ink: '#16233f', ink2: '#4a5672', ink3: '#7d869b', field: '#e9edf2', paper: '#f8f9fb', line: '#cfd6e0', rev: '#2450a6', gold: '#b98f2a', flag: '#b3261e', ok: '#2e7d4f', amber: '#a86a00', fin: '#5b6f9a' };

export interface Camera { k: number; x: number; y: number }

export const toScreen = (c: Camera, x: number, y: number): [number, number] => [(x - c.x) * c.k, (y - c.y) * c.k];

/** A ribbon's outline in screen pixels for a camera: drawn by the renderer, tested by hit testing. */
export function ribbonPath(r: Ribbon, cam: Camera): Path2D {
  const [s0x, s0y] = toScreen(cam, r.x0, r.y0), [s1x, s1y] = toScreen(cam, r.x1, r.y1), [smx] = toScreen(cam, (r.x0 + r.x1) / 2, 0);
  const w = r.w * cam.k, p = new Path2D();
  p.moveTo(s0x, s0y); p.bezierCurveTo(smx, s0y, smx, s1y, s1x, s1y);
  p.lineTo(s1x, s1y + w); p.bezierCurveTo(smx, s1y + w, smx, s0y + w, s0x, s0y + w); p.closePath();
  return p;
}

interface TextOpts { max?: number; min?: number; weight?: number; color?: string; align?: CanvasTextAlign }
interface Line { text: string; weight?: number; color?: string; wrap?: boolean }

/** Draws one frame of a layout. Text is counter-scaled (world size × zoom, clamped), cut to its box, and skipped
 * when the box is shorter than the font; anything that would leave its box is recorded in OVERFLOW. */
export class Renderer {
  readonly OVERFLOW: string[] = [];
  /** when set, every string drawn is appended here (tests read what is on screen) */
  drawn: string[] | null = null;
  private measured = new Map<string, string>();
  private cam: Camera = { k: 1, x: 0, y: 0 };
  private v!: View;
  private VW = 0;
  private VH = 0;

  constructor(private cx: CanvasRenderingContext2D, private g: Graph, private font: string, private cc: Record<string, string>) {}

  clearTextCache() { this.measured.clear(); }

  frame(L: Layout, cam: Camera, VW: number, VH: number, DPR: number, view: View, level: number) {
    this.cam = cam; this.v = view; this.VW = VW; this.VH = VH;
    const cx = this.cx;
    cx.setTransform(DPR, 0, 0, DPR, 0, 0);
    cx.fillStyle = COL.field; cx.fillRect(0, 0, VW, VH);
    for (const r of L.ribbons) this.ribbon(r);
    for (const b of L.boxes) if (this.visible(b)) this.box(b, L, level);
  }

  // ---- policy: what is dimmed, what colour things are ----
  private t = (k: string) => str(this.v.lang, k);
  private nm = (o: Record<string, unknown> | null | undefined) => loc(o, 'name', this.v.lang);
  private amt = (v: number | null | undefined) => fmt(v, this.v.fmt);

  private alpha(id: string, flowId?: string) {
    let a = passesFilter(id, this.v.filt, this.g) ? 1 : 0.14;
    const hl = this.v.hl;
    if (hl) a = Math.min(a, hl.has(id) || (!!flowId && hl.has(flowId)) ? 1 : 0.16);
    return a;
  }

  private ribbonColor(r: Ribbon, f: Flow | undefined) {
    if (this.g.N.get(r.tgt)?.kind === 'category') return this.cc[r.tgt.slice(4)];
    if (f?.kind === 'difference') return COL.flag;
    for (const c of cfg().colorRules ?? []) if (r.src.startsWith(c.prefix) || (c.ribbon === 'either' && r.tgt.startsWith(c.prefix))) return COL[c.color];
    return COL.gold;
  }

  private nodeColor(n: BudgetNode) {
    if (n.kind === 'category') return this.cc[n.id.slice(4)];
    if (n.kind === 'difference' || (n.flags ?? []).includes('RECONCILIATION')) return COL.flag;
    const rule = (cfg().colorRules ?? []).find(c => n.id.startsWith(c.prefix));
    return rule ? COL[rule.color as PaletteKey] : COL.gold;
  }

  // ---- primitives ----
  private S(x: number, y: number) { return toScreen(this.cam, x, y); }

  private visible(b: Box) {
    const [sx, sy] = this.S(b.x, b.y);
    return sx < this.VW && sy < this.VH && sx + b.w * this.cam.k > 0 && sy + b.h * this.cam.k > 0;
  }

  private fit(text: string, px: number, weight: number, maxW: number) {
    const key = weight + '|' + px + '|' + maxW.toFixed(0) + '|' + text;
    let r = this.measured.get(key);
    if (r !== undefined) return r;
    const cx = this.cx;
    cx.font = `${weight} ${px}px ${this.font}`;
    if (cx.measureText(text).width <= maxW) r = text;
    else {
      let lo = 0, hi = text.length;
      while (lo < hi) { const m = (lo + hi + 1) >> 1; if (cx.measureText(text.slice(0, m) + '…').width <= maxW) lo = m; else hi = m - 1; }
      r = lo > 1 ? text.slice(0, lo) + '…' : '';
    }
    if (this.measured.size > 20000) this.measured.clear();
    this.measured.set(key, r);
    return r;
  }

  private txt(text: string, bx: number, by: number, bw: number, bh: number, worldPx: number, opt: TextOpts = {}) {
    const k = this.cam.k, cx = this.cx;
    const px = Math.min(opt.max || 15, Math.max(worldPx * k, 0));
    if (px < (opt.min || 8)) return false;
    const [sx, sy] = this.S(bx, by), sw = bw * k, sh = bh * k;
    if (sh < px * 1.05 || sw < px * 2) return false;
    const P = Math.round(px * 2) / 2;
    const s = this.fit(String(text), P, opt.weight || 400, sw);
    if (!s) return false;
    cx.font = `${opt.weight || 400} ${P}px ${this.font}`;
    cx.fillStyle = opt.color || COL.ink; cx.textBaseline = 'middle';
    cx.textAlign = opt.align || 'left';
    const tx = opt.align === 'right' ? sx + sw : opt.align === 'center' ? sx + sw / 2 : sx;
    if (cx.measureText(s).width > sw + 0.5 || px > sh + 0.01) this.OVERFLOW.push(s);
    this.drawn?.push(s);
    cx.fillText(s, tx, sy + sh / 2);
    return true;
  }

  // several lines inside a box: words wrap, the last line is cut with an ellipsis; nothing is drawn outside the box
  private txtLines(lines: Line[], bx: number, by: number, bw: number, bh: number, worldPx: number, opt: TextOpts = {}) {
    const k = this.cam.k, cx = this.cx;
    const px = Math.min(opt.max || 15, worldPx * k);
    if (px < (opt.min || 8)) return 0;
    const lh = px * 1.25, sh = bh * k, sw = bw * k, room = Math.floor(sh / lh);
    if (room < 1 || sw < px * 2) return 0;
    const P = Math.round(px * 2) / 2;
    cx.font = `${opt.weight || 400} ${P}px ${this.font}`;
    const out: { s: string; L0: Line }[] = [];
    for (const L0 of lines) {
      if (out.length >= room) break;
      cx.font = `${L0.weight || 400} ${P}px ${this.font}`;
      if (!L0.wrap) { out.push({ s: this.fit(L0.text, P, L0.weight || 400, sw), L0 }); continue; }
      const words = String(L0.text).split(' ');
      let cur: string | null = '';
      const maxl = Math.max(1, room - (lines.length - lines.indexOf(L0) - 1) - out.length);
      const mine: string[] = [];
      for (let i = 0; i < words.length; i++) {
        const tryS: string = cur ? cur + ' ' + words[i] : words[i];
        if (cx.measureText(tryS).width <= sw || !cur) cur = tryS;
        else { mine.push(cur); cur = words[i]; if (mine.length === maxl) { cur = null; break; } }
      }
      if (cur) mine.push(cur);
      if (mine.length > maxl) mine.length = maxl;
      const usedAll = mine.join(' ').split(' ').length >= words.length;
      if (!usedAll) mine[mine.length - 1] = mine[mine.length - 1] + ' ' + words.slice(mine.join(' ').split(' ').length).join(' ');
      mine.forEach(m => out.push({ s: this.fit(m, P, L0.weight || 400, sw), L0 }));
    }
    const [sx, sy] = this.S(bx, by), top = sy + (sh - out.length * lh) / 2;
    out.forEach((o, i) => {
      if (!o.s) return;
      cx.font = `${o.L0.weight || 400} ${P}px ${this.font}`;
      cx.fillStyle = o.L0.color || COL.ink; cx.textBaseline = 'middle';
      cx.textAlign = opt.align || 'left';
      const tx = opt.align === 'right' ? sx + sw : sx;
      if (cx.measureText(o.s).width > sw + 0.5) this.OVERFLOW.push(o.s);
      this.drawn?.push(o.s);
      cx.fillText(o.s, tx, top + lh * i + lh / 2);
    });
    return out.length;
  }

  private rect(b: { x: number; y: number; w: number; h: number }, fill: string | null, stroke?: string | null, r = 0) {
    const cx = this.cx, [sx, sy] = this.S(b.x, b.y), w = b.w * this.cam.k, h = b.h * this.cam.k;
    cx.beginPath();
    if (r && w > 2 * r && h > 2 * r) cx.roundRect(sx, sy, w, h, r); else cx.rect(sx, sy, w, h);
    if (fill) { cx.fillStyle = fill; cx.fill(); }
    if (stroke) { cx.strokeStyle = stroke; cx.lineWidth = 1; cx.stroke(); }
  }

  /** compact reconciliation marker that always fits its reserved slot */
  private badgeIn(x: number, y: number, w: number, h: number) {
    const cx = this.cx, [sx, sy] = this.S(x, y), sw = w * this.cam.k, sh = h * this.cam.k, s = Math.min(sw - 2, sh - 2, 16);
    if (s < 9) return;
    cx.fillStyle = COL.flag; cx.beginPath(); cx.roundRect(sx + sw - s, sy + (sh - s) / 2, s, s, 3); cx.fill();
    cx.fillStyle = '#fff'; cx.font = `700 ${Math.round(s * 0.7)}px ${this.font}`; cx.textAlign = 'center'; cx.textBaseline = 'middle';
    cx.fillText('≠', sx + sw - s / 2, sy + sh / 2 + 0.5);
  }

  private badge(x: number, y: number, kind: string) {
    const cx = this.cx, [sx, sy] = this.S(x, y);
    if (this.cam.k < 0.15) return;
    cx.font = `700 10px ${this.font}`;
    const w = cx.measureText(kind).width + 10;
    cx.fillStyle = kind === 'RECONCILIATION' ? COL.flag : COL.amber; cx.beginPath(); cx.roundRect(sx, sy, w, 16, 3); cx.fill();
    cx.fillStyle = '#fff'; cx.textBaseline = 'middle'; cx.textAlign = 'left'; cx.fillText(kind, sx + 5, sy + 8.5);
  }

  // ---- what each kind of box looks like ----
  private ribbon(r: Ribbon) {
    const [s0x] = this.S(r.x0, 0), [s1x] = this.S(r.x1, 0);
    if (Math.max(s0x, s1x) < 0 || Math.min(s0x, s1x) > this.VW) return;
    const cx = this.cx, p = ribbonPath(r, this.cam);
    const sel = this.v.selFlow === r.id || !!this.v.hl?.has(r.id);
    cx.globalAlpha = (sel ? 0.85 : 0.38) * Math.min(this.alpha(r.tgt, r.id), this.alpha(r.src, r.id));
    cx.fillStyle = this.ribbonColor(r, this.g.F.get(r.id)); cx.fill(p);
    if (sel) { cx.globalAlpha = 1; cx.strokeStyle = COL.ink; cx.lineWidth = 1.2; cx.stroke(p); }
    cx.globalAlpha = 1;
  }

  private box(b: Box, L: Layout, lv: number) {
    switch (b.t) {
      case 'stitle': this.txt(this.t(b.key), b.x, b.y, b.w, b.h, 120, { weight: 650, max: 30, min: 9 }); return;
      case 'chead': this.txt(this.t(b.key), b.x, b.y, b.w, b.h, 30, { weight: 600, color: COL.ink2, max: 15 }); return;
      case 'note': this.txt(this.t(b.key), b.x, b.y, b.w, b.h, 26, { color: COL.ink2, max: 13 }); return;
      case 'snode': return this.snode(b);
      case 'card': return this.card(b, L, lv);
      case 'row': return this.row(b, lv);
      case 'prow': return this.prow(b, lv);
      case 'prest': return this.prest(b);
      case 'check': return this.check(b);
      case 'finding': return this.finding(b);
    }
  }

  private snode(b: BoxOf<'snode'>) {
    const n = this.g.N.get(b.id)!, cx = this.cx;
    cx.globalAlpha = this.alpha(b.id);
    this.rect(b, this.nodeColor(n), null, 2);
    if (this.v.sel === b.id) this.rect({ x: b.x - 4, y: b.y - 4, w: b.w + 8, h: b.h + 8 }, null, COL.ink, 3);
    const lab = this.nm(n), amt = this.amt(isNegative(n.id) ? -n.amount : n.amount);
    const rec = !!n.flags?.includes('RECONCILIATION');
    const bw = rec ? 64 : 0; // room reserved for the badge inside the label lane
    const big = b.h >= 100;
    const drawn = this.txtLines(big ? [{ text: lab, weight: 600, wrap: true }, { text: amt, color: COL.ink2 }] : [{ text: lab + '  ' + amt }],
      b.lx, b.y, b.lw - bw, b.h, big ? 40 : 30, { align: b.labelLeft ? 'right' : 'left', max: big ? 14 : 12.5 });
    if (rec && drawn) this.badgeIn(b.labelLeft ? b.lx : b.lx + b.lw - bw, b.y, bw, b.h);
    cx.globalAlpha = 1;
  }

  private card(b: BoxOf<'card'>, L: Layout, lv: number) {
    const cx = this.cx, g = this.g, v = this.v, k = this.cam.k, p = 18;
    const n = g.N.get(b.id)!, a = this.alpha(b.id);
    cx.globalAlpha = a;
    this.rect(b, '#fff', v.sel === b.id ? COL.ink : COL.line, 8);
    if (v.sel === b.id) { const [sx, sy] = this.S(b.x, b.y); cx.lineWidth = 2.5; cx.strokeStyle = COL.ink; cx.strokeRect(sx, sy, b.w * k, b.h * k); }
    // level 1: name, amount, bar proportional to the largest card
    this.txt(this.nm(n), b.x + p, b.y + 10, b.w - 2 * p, 46, 32, { weight: 650, max: 15, min: 7 });
    this.txt(this.amt(n.amount), b.x + p, b.y + 58, b.w - 2 * p - 140, 40, 30, { color: COL.ink2, max: 14, min: 7 });
    if (n.code) this.txt('#' + n.code, b.x + b.w - p - 130, b.y + 58, 130, 40, 22, { color: COL.ink3, align: 'right', max: 12 });
    this.rect({ x: b.x + p, y: b.y + 104, w: (b.w - 2 * p) * Math.max(b.rel, 0.004), h: 10 }, COL.gold);
    const flag = (n.flags ?? []).find(f => f === 'RECONCILIATION' || f === 'AMBIGUITY');
    if (flag && CARD_GAP * k >= 20) this.badge(b.x + b.w - p - 150, b.y - 19 / k, flag);
    // level 2: the economic-category bar
    for (const s of b.segs) {
      cx.globalAlpha = a * (v.filt.cats.has(s.c) ? 1 : 0.15) * (v.hl ? ((s.flow && v.hl.has(s.flow)) || v.hl.has(n.id) ? 1 : 0.2) : 1);
      this.rect(s, this.cc[s.c]);
      if (v.selFlow && v.selFlow === s.flow) this.rect(s, null, COL.ink);
      if (lv >= 1) this.txt(pct(s.share), s.x + 3, s.y, s.w - 6, s.h, 13, { color: '#fff', max: 11, min: 8 });
    }
    cx.globalAlpha = a;
    if (lv >= 1) {
      const staff = n.staff ? `${this.t('staff')}: ${nf0().format(n.staff)}` : '';
      const chg = n.prev ? (n.amount / n.prev - 1) * 100 : 0;
      const srcs = (n.prev ? `${this.t('prevYear')}: ${chg >= 0 ? '+' : ''}${chg.toFixed(1)}%   ` : '') + (n.sources ? Object.entries(n.sources).map(([key, s]) => `${key.toUpperCase()} ${fmt(s.amount, 'short')}`).join(' · ') : '');
      this.txt([staff, srcs].filter(Boolean).join('   '), b.x + p, b.y + 147, b.w - 2 * p, 18, 13, { color: COL.ink2, max: 11 });
    }
    // skeleton of what is inside: programmes at level 1, everything deeper until level 3
    cx.globalAlpha = a * 0.5;
    const kids = lv === 2 ? [] : rowsFor(g, n).filter(r => (lv === 0 ? r.depth === 0 : r.depth > 0));
    const mx = Math.max(1, ...kids.map(r => Math.abs(r.n.amount)));
    for (const r of kids) {
      const rb = L.byId.get(r.n.id);
      if (rb) this.rect({ x: rb.x, y: rb.y + rb.h * 0.3, w: (rb.w * Math.abs(r.n.amount)) / mx, h: Math.max(rb.h * 0.4, 1) }, COL.line);
    }
    cx.globalAlpha = 1;
  }

  private row(b: BoxOf<'row'>, lv: number) {
    if (lv < 1 || (lv < 2 && b.depth > 0)) return;
    const n = this.g.N.get(b.id)!, cx = this.cx;
    cx.globalAlpha = this.alpha(b.id);
    const isDiff = n.kind === 'difference';
    if (this.v.sel === b.id) this.rect(b, '#fff3c4');
    else if (b.depth === 0) this.rect(b, isDiff ? '#fbe3e1' : COL.paper);
    else if (isDiff) this.rect(b, '#fbe3e1');
    const fs = b.depth === 0 ? 13 : 11.5, weight = b.depth === 0 ? 600 : 400;
    this.txt(this.amt(n.amount), b.x, b.y, b.w - 4, b.h, fs, { align: 'right', color: isDiff ? COL.flag : COL.ink2, max: 13, min: 7, weight });
    const amw = Math.min(150, b.w * 0.34);
    this.txt((n.code && n.kind === 'subprogramme' ? n.code + '  ' : '') + this.nm(n), b.x + 4, b.y, b.w - amw - 8, b.h, fs, { weight, color: isDiff ? COL.flag : COL.ink, max: 13, min: 7 });
    cx.globalAlpha = 1;
  }

  private prow(b: BoxOf<'prow'>, lv: number) {
    const n = this.g.N.get(b.id)!, cx = this.cx;
    cx.globalAlpha = this.alpha(b.id);
    this.rect(b, this.v.sel === b.id ? '#fff3c4' : '#fff', COL.line, 4);
    const cat = rankingFor(n.kind)?.category;
    this.rect({ x: b.x, y: b.y + b.h - 4, w: b.w * b.rel, h: 4 }, (cat && this.cc[cat]) || COL.gold);
    this.txt(b.rank + '.', b.x + 6, b.y, 56, b.h - 4, 24, { color: COL.ink3, max: 12 });
    this.txt(this.amt(n.amount), b.x + b.w - 210, b.y, 202, b.h - 4, 24, { align: 'right', weight: 600, max: 13 });
    const [nw, ow] = lv >= 1 ? [0.55, 0.45] : [0.62, 0.38];
    this.txt(this.nm(n), b.x + 66, b.y, b.w * nw, b.h - 4, 24, { max: lv >= 1 ? 12.5 : 12 });
    this.txt(n.owner ? this.g.nameOf(n.owner, this.v.lang) : '', b.x + 72 + b.w * nw, b.y, b.w * ow - 290, b.h - 4, 22, { color: COL.ink2, max: 11.5 });
    cx.globalAlpha = 1;
  }

  private prest(b: BoxOf<'prest'>) {
    this.txt(`+ ${nf0().format(b.count)} ${this.t('more')} · ${this.amt(b.sum)}  (${nf0().format(b.all)} · ${this.amt(b.allSum)})`, b.x, b.y, b.w, b.h, 24, { color: COL.ink2, max: 13 });
  }

  private check(b: BoxOf<'check'>) {
    const c = b.chk, k = clsOf(c), col = CLSCOL[k], v = this.v, cx = this.cx;
    cx.globalAlpha = (v.hl ? (v.hl.has(b.id) ? 1 : 0.2) : 1) * (v.clsFilter && v.clsFilter !== k ? 0.15 : 1);
    this.rect(b, v.sel === b.id ? '#fff3c4' : '#fff', k === 'pass' ? COL.line : col, 5);
    this.rect({ x: b.x, y: b.y, w: 8, h: b.h }, col);
    this.txt(clsName(k, v.lang), b.x + 16, b.y, 200, b.h, 20, { weight: 600, color: col, max: 12 });
    this.txt(loc(c, 'title', v.lang), b.x + 226, b.y, b.w - 690, b.h, 20, { max: 12.5 });
    const d = c.kind === 'count' ? `${nf0().format(c.actual ?? 0)} ${this.t(c.actual === 1 ? 'case1' : 'caseN')}` : `${this.t('diff')} ${ckv(c, c.diff, v.fmt)}`;
    this.txt(k === 'pass' ? '0' : d, b.x + b.w - 450, b.y, 300, b.h, 20, { align: 'right', weight: 600, color: k === 'pass' ? COL.ink2 : col, max: 12.5 });
    this.txt('p. ' + c.pages.slice(0, 4).join(', ') + (c.pages.length > 4 ? '…' : ''), b.x + b.w - 140, b.y, 132, b.h, 18, { align: 'right', color: COL.ink3, max: 11.5 });
    cx.globalAlpha = 1;
  }

  private finding(b: BoxOf<'finding'>) {
    const f = b.f, v = this.v, cx = this.cx;
    this.rect(b, v.sel === b.id ? '#fff3c4' : '#fff', COL.line, 5);
    const fk = findingCls(f);
    cx.globalAlpha = v.clsFilter && v.clsFilter !== fk ? 0.15 : 1;
    this.rect({ x: b.x, y: b.y, w: 8, h: b.h }, fk ? CLSCOL[fk] : f.type === 'ambiguity' ? COL.amber : COL.ink3);
    this.txt((fk ? clsName(fk, v.lang) + ' · ' : '') + loc(f, 'title', v.lang) + (f.diff != null ? `  (${this.t('diff')} ${findingDiff(f, v.fmt)})` : ''), b.x + 16, b.y, b.w - 160, b.h, 18, { max: 12 });
    this.txt(f.pages && f.pages.length ? 'p. ' + f.pages.join(', ') : '', b.x + b.w - 150, b.y, 142, b.h, 17, { align: 'right', color: COL.ink3, max: 11.5 });
    cx.globalAlpha = 1;
  }
}

export const categoryColors = (css: CSSStyleDeclaration) => Object.fromEntries(catIds().map(c => [c, css.getPropertyValue('--c-' + c).trim()]));
