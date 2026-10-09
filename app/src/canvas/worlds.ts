import { checksTabId, sankeyTabs, tabById, tabForChunk, tabIds } from '../config';
import type { Graph } from '../data/graph';
import { buildLayout, type Box, type Layout } from './layout';

/** Each tab's world, laid out the first time it is needed, and which world can show a given node or flow. */
export class Worlds {
  readonly built: Record<string, Layout | null> = {};

  constructor(private g: Graph, private sortOf: (tab: string) => string | undefined) {}

  get(tab: string) { return this.built[tab] ?? null; }

  async prepare(tab: string): Promise<Layout> {
    const have = this.built[tab];
    if (have) return have;
    await this.g.loadChunk(tabById(tab)?.chunk);
    return (this.built[tab] ??= buildLayout(tabById(tab)!, this.g, this.sortOf(tab)));
  }

  /** Lay a tab out again (its sort order changed). */
  invalidate(tab: string) { this.built[tab] = null; }

  /** Where a node is drawn itself: checks and findings on the checks tab, everything else by its data chunk. */
  naturalTab(id: string) {
    if (id.startsWith('check:') || id.startsWith('finding:')) return checksTabId();
    return tabForChunk(this.g.chunkOf(id));
  }

  /** The box showing a node in a world: its own, or (unless `direct`) that of its anchor, owner or nearest drawn ancestor. */
  boxIn(L: Layout, id: string, direct: boolean): Box | null {
    const b = L.byId.get(id);
    if (b || direct) return b ?? null;
    const n = this.g.N.get(id);
    if (!n) return null;
    if (n.anchor) return L.byId.get(n.anchor) ?? null;
    if (n.owner) return L.byId.get(n.owner) ?? null;
    if (n.parent) return this.boxIn(L, n.parent, false);
    return null;
  }

  /** The tab that can show a node, preferring one where it is drawn itself; `current` wins ties after its own tab. */
  async tabFor(id: string, current: string): Promise<string> {
    await this.g.ensure(id);
    const nat = this.naturalTab(id);
    const order = [nat, current, ...tabIds()].filter((t, i, a) => a.indexOf(t) === i);
    for (const direct of [true, false]) for (const tb of order) {
      // never open a ranking tab just to show an owner
      if (!direct && tabById(tb)?.layout === 'ranking' && nat !== tb) continue;
      if (this.boxIn(await this.prepare(tb), id, direct)) return tb;
    }
    return current;
  }

  /** The sankey tab that draws a flow as a ribbon, if any. */
  async tabForRibbon(fid: string): Promise<string | null> {
    for (const t of sankeyTabs()) if ((await this.prepare(t.id)).ribbons.some(r => r.id === fid)) return t.id;
    return null;
  }
}
