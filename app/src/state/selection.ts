import type { Graph } from '../data/graph';
import type { Tour } from '../types';
import type { Filters, UIState } from './store';

// The panel is the selection. What the canvas marks as selected, and what a tour lights up, follow from the panel and
// the tour; they are never stored separately, so no action can leave them out of step.

/** The selected box: a node, or 'check:<id>' / 'finding:<index>' on the checks tab. */
export function selectedId(s: UIState): string | null {
  const p = s.panel;
  if (p?.type === 'node') return p.id;
  if (p?.type === 'check') return 'check:' + p.check.id;
  if (p?.type === 'finding') return 'finding:' + p.idx;
  return null;
}

/** The selected ribbon: the flow in the panel, or during a tour the flow of the step being shown. */
export function selectedFlow(s: UIState): string | null {
  const p = s.panel;
  if (p?.type === 'flow') return p.id;
  const st = s.tour?.steps[s.step];
  return st && p?.type === 'node' && p.id === st.node ? st.flow || null : null;
}

const lit = new WeakMap<Tour, Set<string>[]>();

/** Everything a tour has visited up to its current step stays lit; the rest is dimmed. Null outside tours. */
export function tourHighlight(s: UIState, g: Graph): Set<string> | null {
  const tr = s.tour;
  if (!tr) return null;
  let steps = lit.get(tr);
  if (!steps) lit.set(tr, (steps = []));
  return (steps[s.step] ??= visited(tr, s.step, g));
}

function visited(tr: Tour, step: number, g: Graph) {
  const out = new Set<string>();
  for (const st of tr.steps.slice(0, step + 1)) {
    out.add(st.node);
    const f = st.flow ? g.F.get(st.flow) : undefined;
    if (f) { out.add(f.id); out.add(f.source); out.add(f.target); }
  }
  return out;
}

/** What the canvas needs from the interface state to draw a frame. */
export interface View {
  lang: string;
  fmt: UIState['fmt'];
  sel: string | null;
  selFlow: string | null;
  hl: Set<string> | null;
  filt: Filters;
  clsFilter: UIState['clsFilter'];
}

export const viewOf = (s: UIState, g: Graph): View => ({
  lang: s.lang, fmt: s.fmt, sel: selectedId(s), selFlow: selectedFlow(s), hl: tourHighlight(s, g), filt: s.filt, clsFilter: s.clsFilter,
});
