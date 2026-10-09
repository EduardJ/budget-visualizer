import { catIds, cfg } from '../config';
import type { Graph } from '../data/graph';
import { clsOf } from '../checks';
import type { BudgetNode, CardsTab, Check, ChecksTab, Finding, RankingTab, SankeyTab, TabConfig } from '../types';

// Everything is laid out once per tab in world units. Zoom never moves anything; it only changes what is drawn.
// A layout is immutable once built: drawing and hit testing only read it.

interface Rect { x: number; y: number; w: number; h: number }
interface At extends Rect { id: string }

/** One economic category's share of a card's bar; clicking it opens the flow organisation -> category. */
export interface Segment extends Rect { c: string; share: number; flow?: string }

export type Box =
  | At & { t: 'stitle' | 'chead' | 'note'; key: string }
  /** a sankey bar, with its label lane at lx..lx+lw on one side */
  | At & { t: 'snode'; col: number; lx: number; lw: number; labelLeft: boolean }
  | At & { t: 'card'; sec: string; rel: number; segs: Segment[] }
  | At & { t: 'row'; sec: string; depth: number; card: string }
  | At & { t: 'prow'; rank: number; rel: number }
  | At & { t: 'prest'; count: number; sum: number; all: number; allSum: number }
  | At & { t: 'check'; chk: Check }
  | At & { t: 'finding'; f: Finding; idx: number };

export type BoxOf<T extends Box['t']> = Extract<Box, { t: T }>;

export interface Ribbon { id: string; x0: number; y0: number; x1: number; y1: number; w: number; src: string; tgt: string }

export interface Layout {
  tab: TabConfig;
  boxes: Box[];
  byId: Map<string, Box>;
  ribbons: Ribbon[];
  w: number;
  h: number;
}

const BAR_W = 26;
const CARD_W = 470, HEAD_H = 170, CARD_PAD = 18;
export const CARD_GAP = 40;
const ROW_H: Record<number, number> = { 0: 22, 1: 17, 2: 15 };
const RANK_ROW_W = 960, RANK_ROW_H = 34;
const CHECK_ROW_W = 1460, CHECK_ROW_H = 48;

export const emptyLayout = (tab: TabConfig): Layout => ({ tab, boxes: [], byId: new Map(), ribbons: [], w: 0, h: 0 });

/** Right edge of a box including a sankey label lane. */
const right = (b: Box) => b.x + (b.t === 'snode' ? Math.max(b.w, b.lx + b.lw - b.x) : b.w);

export function buildLayout(tab: TabConfig, g: Graph, sort?: string): Layout {
  const L = emptyLayout(tab);
  const add = (b: Box) => { L.boxes.push(b); if (!L.byId.has(b.id)) L.byId.set(b.id, b); };
  const title = (key: string, w: number) => { add({ t: 'stitle', id: 'sec:' + key, x: 0, y: 0, w, h: 150, key }); return 190; };
  const ctx: Ctx = { g, L, add, title };
  if (tab.layout === 'sankey') sankey(ctx, tab);
  else if (tab.layout === 'cards') cards(ctx, tab, sort);
  else if (tab.layout === 'ranking') ranking(ctx, tab);
  else checks(ctx, tab);
  L.w = Math.max(...L.boxes.map(right));
  L.h = Math.max(...L.boxes.map(b => b.y + b.h));
  return L;
}

interface Ctx { g: Graph; L: Layout; add: (b: Box) => void; title: (key: string, w: number) => number }

function sankey({ g, L, add, title }: Ctx, tab: SankeyTab) {
  const y = title(tab.title, tab.width ?? 3200);
  const inflows = g.N.get(cfg().totals.inflows ?? cfg().totals.budget);
  const s = (tab.height ?? 1500) / (inflows ? inflows.amount : 1);
  const ids = new Set(tab.columns.flatMap(c => c.nodes));
  const bars = new Map<string, BoxOf<'snode'>>();
  tab.columns.forEach((col, ci) => {
    let cy = y + 50;
    const left = col.labelSide === 'left', lw = col.labelWidth ?? 330;
    for (const id of col.nodes) {
      const n = g.N.get(id);
      if (!n) continue;
      const h = Math.max(46, Math.abs(n.amount) * s);
      const b: BoxOf<'snode'> = { t: 'snode', id, x: col.x, y: cy, w: BAR_W, h, col: ci, lx: left ? col.x - lw - 10 : col.x + BAR_W + 8, lw, labelLeft: left };
      add(b); bars.set(id, b);
      cy += h + 12;
    }
  });
  tab.columns.forEach((col, ci) => {
    const lw = col.labelWidth ?? 330;
    if (col.labelSide === 'left') add({ t: 'chead', id: 'ch' + ci, x: col.x - lw - 10, y: y - 20, w: lw + 10 + BAR_W, h: 44, key: col.header });
    else add({ t: 'chead', id: 'ch' + ci, x: col.x, y: y - 20, w: col.headerWidth ?? 300, h: 44, key: col.header });
  });
  // ribbons: outgoing stacked by target y, incoming by source y, both centred on the bar
  const bar = (id: string) => bars.get(id)!;
  const sk = g.D.flows.filter(f => ids.has(f.source) && ids.has(f.target) && f.amount > 0 && bars.has(f.source) && bars.has(f.target));
  const inSk = new Set(sk);
  const outOff = new Map<string, number>(), inOff = new Map<string, number>();
  for (const id of ids) {
    const b = bars.get(id);
    if (!b) continue;
    const so = (g.OUT.get(id) ?? []).filter(f => inSk.has(f)).reduce((a, f) => a + f.amount * s, 0);
    const si = (g.IN.get(id) ?? []).filter(f => inSk.has(f)).reduce((a, f) => a + f.amount * s, 0);
    outOff.set(id, b.y + (b.h - so) / 2);
    inOff.set(id, b.y + (b.h - si) / 2);
  }
  const tgtY = new Map<string, number>();
  for (const f of [...sk].sort((a, b) => bar(a.source).y - bar(b.source).y)) {
    const o = inOff.get(f.target)!;
    tgtY.set(f.id, o);
    inOff.set(f.target, o + f.amount * s);
  }
  for (const f of [...sk].sort((a, b) => bar(a.target).y - bar(b.target).y)) {
    const ys = outOff.get(f.source)!;
    outOff.set(f.source, ys + f.amount * s);
    L.ribbons.push({ id: f.id, x0: bar(f.source).x + BAR_W, y0: ys, x1: bar(f.target).x, y1: tgtY.get(f.id)!, w: Math.max(0.6, f.amount * s), src: f.source, tgt: f.target });
  }
}

/** A card's rows: every descendant except projects, depth first. */
export function rowsFor(g: Graph, n: BudgetNode) {
  const out: { n: BudgetNode; depth: number }[] = [];
  const walk = (p: BudgetNode, depth: number) => {
    for (const k of (g.KIDS.get(p.id) ?? []).filter(k => k.kind !== 'project')) { out.push({ n: k, depth }); walk(k, depth + 1); }
  };
  walk(n, 0);
  return out;
}

function sortCards(list: BudgetNode[], tab: CardsTab, sort: string | undefined) {
  const opt = tab.sort?.find(o => o.id === sort);
  const share = (n: BudgetNode, c: string) => (n.cats?.[c] ?? 0) / n.amount;
  if (opt?.share) { const c = opt.share; return list.sort((a, b) => share(b, c) - share(a, c)); }
  if (opt?.id === 'name') { const lang = cfg().sourceLang, k = 'name_' + lang; return list.sort((a, b) => String(a[k]).localeCompare(String(b[k]), lang)); }
  return list.sort((a, b) => b.amount - a.amount);
}

/** The bar split by economic category, each segment the flow from the organisation to that category. */
function segments(g: Graph, n: BudgetNode, x: number, y: number): Segment[] {
  const cats = n.cats ?? {}, bw = CARD_W - 2 * CARD_PAD;
  const tot = Object.values(cats).reduce((s, v) => s + Math.max(v, 0), 0) || 1;
  const out: Segment[] = [];
  let sx = x + CARD_PAD;
  for (const c of catIds()) {
    const v = cats[c];
    if (!v || v <= 0) continue;
    const w = (bw * v) / tot;
    out.push({ x: sx, y: y + 122, w, h: 22, c, share: v / tot, flow: (g.OUT.get(n.id) ?? []).find(f => f.target === 'cat:' + c)?.id });
    sx += w;
  }
  return out;
}

function cards({ g, add, title }: Ctx, tab: CardsTab, sort: string | undefined) {
  const cols = tab.columns ?? 8;
  const list = sortCards([...g.N.values()].filter(n => n.kind === tab.kind), tab, sort);
  let y = title(tab.title, cols * (CARD_W + CARD_GAP));
  if (tab.note) { add({ t: 'note', id: 'note:' + tab.id, x: 0, y: y - 16, w: cols * (CARD_W + CARD_GAP) - 40, h: 48, key: tab.note }); y += 70; }
  const colY = Array(cols).fill(y);
  const maxAmt = Math.max(...list.map(n => n.amount));
  for (const n of list) {
    const rows = rowsFor(g, n);
    const h = HEAD_H + rows.reduce((a, r) => a + ROW_H[Math.min(r.depth, 2)], 0) + 16;
    let ci = 0;
    for (let i = 1; i < cols; i++) if (colY[i] < colY[ci] - 0.5) ci = i;
    const cx = ci * (CARD_W + CARD_GAP), cy = colY[ci];
    add({ t: 'card', id: n.id, x: cx, y: cy, w: CARD_W, h, sec: tab.id, rel: n.amount / maxAmt, segs: segments(g, n, cx, cy) });
    let ry = cy + HEAD_H;
    for (const r of rows) {
      const rh = ROW_H[Math.min(r.depth, 2)];
      add({ t: 'row', id: r.n.id, x: cx + 12 + r.depth * 14, y: ry, w: CARD_W - 24 - r.depth * 14, h: rh - 2, depth: r.depth, sec: tab.id, card: n.id });
      ry += rh;
    }
    colY[ci] = cy + h + CARD_GAP;
  }
}

function ranking({ g, add, title }: Ctx, tab: RankingTab) {
  const topN = tab.top ?? 150, per = tab.perColumn ?? 50;
  const P = [...g.N.values()].filter(n => n.kind === tab.kind && n.amount > 0).sort((a, b) => b.amount - a.amount);
  const top = P.slice(0, topN), cols = Math.max(1, Math.ceil(top.length / per));
  const y = title(tab.title, cols * (RANK_ROW_W + 40));
  const max = top.length ? top[0].amount : 1;
  top.forEach((n, i) => {
    const c = Math.floor(i / per), r = i % per;
    add({ t: 'prow', id: n.id, x: c * (RANK_ROW_W + 40), y: y + r * RANK_ROW_H, w: RANK_ROW_W, h: RANK_ROW_H - 4, rank: i + 1, rel: n.amount / max });
  });
  const rest = P.slice(topN);
  add({ t: 'prest', id: 'prest', x: 0, y: y + per * RANK_ROW_H + 16, w: RANK_ROW_W * cols + 40 * (cols - 1), h: 40,
        count: rest.length, sum: rest.reduce((a, n) => a + n.amount, 0), all: P.length, allSum: P.reduce((a, n) => a + n.amount, 0) });
}

const RANK = { error: 0, rounding: 1, pass: 2 } as const;
const findingRank = (f: Finding) => (f.type === 'mismatch' ? (f.cls === 'rounding' ? 1 : 0) : 2);

/** Two columns of checks, errors first, then two columns of findings. */
function checks({ g, add, title }: Ctx, tab: ChecksTab) {
  const RW = CHECK_ROW_W, RH = CHECK_ROW_H;
  const y = title(tab.title, 3000);
  const list = [...g.D.checks].sort((a, b) => RANK[clsOf(a)] - RANK[clsOf(b)]);
  const half = Math.ceil(list.length / 2);
  list.forEach((c, i) => {
    const col = i < half ? 0 : 1, r = col ? i - half : i;
    add({ t: 'check', id: 'check:' + c.id, chk: c, x: col * (RW + 40), y: y + r * RH, w: RW, h: RH - 6 });
  });
  let fy = y + half * RH + 40;
  add({ t: 'chead', id: 'fh', x: 0, y: fy, w: 900, h: 44, key: 'findings' });
  fy += 60;
  const F = g.D.findings, fhalf = Math.ceil(F.length / 2);
  F.map((f, idx) => ({ f, idx })).sort((a, b) => findingRank(a.f) - findingRank(b.f)).forEach(({ f, idx }, i) => {
    const col = i < fhalf ? 0 : 1, r = col ? i - fhalf : i;
    add({ t: 'finding', id: 'finding:' + idx, f, idx, x: col * (RW + 40), y: fy + r * 44, w: RW, h: 38 });
  });
}
