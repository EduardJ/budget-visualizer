import type { BudgetNode, Chunk, CoreData, Dict, Flow, Ref, SearchRow } from '../types';
import type { DataSource } from './source';
import { cfg } from '../config';
import { loc } from '../i18n';

/** Everything loaded so far, indexed for the renderer and the panel. Chunks are added in the order they were requested. */
export class Graph {
  readonly N = new Map<string, BudgetNode>();
  readonly F = new Map<string, Flow>();
  readonly REFS: Dict<Ref> = {};
  readonly KIDS = new Map<string, BudgetNode[]>();
  readonly OUT = new Map<string, Flow[]>();
  readonly IN = new Map<string, Flow[]>();
  readonly LOADED = new Set<string>();
  readonly SIDX: Map<string, SearchRow>;
  readonly PERF: Dict<number> = {};
  private pending = new Map<string, Promise<void>>();
  private applied: Promise<void> = Promise.resolve();

  constructor(readonly D: CoreData, private source: DataSource) {
    this.add(D);
    this.LOADED.add('core');
    this.SIDX = new Map(D.search.map(r => [r[0], r]));
  }

  private add(c: Chunk) {
    for (const n of c.nodes) {
      this.N.set(n.id, n);
      if (n.parent) push(this.KIDS, n.parent, n);
    }
    for (const f of c.flows) {
      this.F.set(f.id, f);
      push(this.OUT, f.source, f);
      push(this.IN, f.target, f);
    }
    Object.assign(this.REFS, c.refs);
  }

  loadChunk(k: string | undefined): Promise<void> {
    if (!k || this.LOADED.has(k)) return Promise.resolve();
    let p = this.pending.get(k);
    if (!p) {
      const t0 = performance.now();
      const data = this.source.chunk(k);
      // fetched in parallel, applied in request order so maps and child lists are always built the same way
      p = this.applied.then(() => data).then(c => {
        this.add(c);
        this.LOADED.add(k);
        this.PERF[k] = Math.round(performance.now() - t0);
      });
      this.applied = p.catch(() => {});
      this.pending.set(k, p);
      p.finally(() => this.pending.delete(k)).catch(() => {});
    }
    return p;
  }

  /** Load whatever a node and its details panel need. */
  async ensure(id: string) {
    const r = this.SIDX.get(id);
    await Promise.all([this.loadChunk(r?.[7]), ...(this.D.need[id] ?? []).map(k => this.loadChunk(k))]);
  }

  async ensureFlow(fid: string) {
    if (!this.F.has(fid) && this.D.flowChunk?.[fid]) await this.loadChunk(this.D.flowChunk[fid]);
  }

  chunkOf(id: string) { return this.SIDX.get(id)?.[7] ?? 'core'; }

  /** A node's name without loading its chunk: the search index has every name. */
  nameOf(id: string, lang: string): string {
    const n = this.N.get(id), r = this.SIDX.get(id);
    return loc(n ?? (r && { ['name_' + cfg().sourceLang]: r[1], name_en: r[2] }), 'name', lang);
  }

  /** A node's amount without loading its chunk. */
  amountOf(id: string): number | undefined { return this.N.get(id)?.amount ?? this.SIDX.get(id)?.[3]; }
}

function push<T>(m: Map<string, T[]>, k: string, v: T) {
  const a = m.get(k);
  if (a) a.push(v); else m.set(k, [v]);
}
