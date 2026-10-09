import { useSyncExternalStore } from 'react';
import type { AmountFormat } from '../format';
import type { Check, Finding, Kpi, ReconFilter, Tour } from '../types';

export type PanelView =
  | { type: 'node'; id: string }
  | { type: 'flow'; id: string }
  | { type: 'check'; check: Check }
  | { type: 'finding'; finding: Finding; idx: number }
  | { type: 'kpi'; kpi: Kpi };

export interface Filters { cats: Set<string>; levels: Record<string, boolean>; min: number }

/** Everything the interface shows, apart from the camera (which changes every frame and lives in the engine). */
export interface UIState {
  lang: string;
  fmt: AmountFormat;
  tab: string;
  tour: Tour | null;
  step: number;
  filt: Filters;
  sorts: Record<string, string>;
  clsFilter: ReconFilter | null;
  /** what the details panel shows, which is also what is selected (state/selection.ts) */
  panel: PanelView | null;
  /** bumps on every panel open, so the panel scrolls back to the top */
  panelSeq: number;
  menu: 'filters' | 'tours' | null;
  recon: boolean;
  level: number;
  loading: boolean;
  toast: { msg: string; seq: number } | null;
  hist: { memory: boolean; canBack: boolean; canFwd: boolean };
}

type Listener = () => void;

export class Store<S extends object> {
  private listeners = new Set<Listener>();
  constructor(private s: S) {}
  get = (): S => this.s;
  set(patch: Partial<S>) {
    this.s = { ...this.s, ...patch };
    for (const l of this.listeners) l();
  }
  subscribe = (l: Listener) => {
    this.listeners.add(l);
    return () => { this.listeners.delete(l); };
  };
}

let store: Store<UIState> | null = null;

export function createStore(init: UIState) {
  store = new Store(init);
  return store;
}

export function ui(): Store<UIState> {
  if (!store) throw new Error('store not created');
  return store;
}

export function useUI<T>(select: (s: UIState) => T): T {
  const s = ui();
  return useSyncExternalStore(s.subscribe, () => select(s.get()));
}
