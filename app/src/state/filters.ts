import { catIds, cfg, rankingFor, sectionOfChunk } from '../config';
import type { Graph } from '../data/graph';
import type { BudgetNode } from '../types';
import type { Filters } from './store';

// Filters dim, they never hide or move anything: a node that fails them is drawn faintly in its usual place.

const SIZED_KINDS = ['programme', 'subprogramme', 'project', 'org', 'municipality'];

/** A project belongs to its owner's section; its owner's data may not be loaded yet. */
function sectionOf(n: BudgetNode, g: Graph) {
  if (n.kind !== 'project' || !n.owner) return n.section;
  return g.N.get(n.owner)?.section ?? sectionOfChunk(g.chunkOf(n.owner));
}

export function passesFilter(id: string, F: Filters, g: Graph): boolean {
  const n = g.N.get(id);
  if (!n) return true;
  const sec = sectionOf(n, g);
  for (const lvl of cfg().levels ?? []) {
    if (F.levels[lvl.id] === false && ((sec && lvl.sections.includes(sec)) || lvl.nodes?.includes(id))) return false;
  }
  if (F.min > 0 && SIZED_KINDS.includes(n.kind) && Math.abs(n.amount) < F.min) return false;
  if (F.cats.size < catIds().length) {
    if (n.kind === 'category') return F.cats.has(id.slice(4));
    if (n.cats) return Object.keys(n.cats).some(c => F.cats.has(c) && n.cats![c]);
    const cat = rankingFor(n.kind)?.category;
    if (cat) return F.cats.has(cat);
  }
  return true;
}
