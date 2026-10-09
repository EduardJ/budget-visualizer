import { createContext, useContext, useEffect, useState, type MouseEvent, type ReactNode } from 'react';
import { pdfHref } from '../config';
import type { Controller } from '../controller';
import type { Graph } from '../data/graph';
import type { DataSource } from '../data/source';
import { change, fmt, type AmountFormat } from '../format';
import { loc, str } from '../i18n';
import { useUI } from '../state/store';

export interface Runtime { g: Graph; c: Controller; source: DataSource }
export const RuntimeContext = createContext<Runtime | null>(null);

export function useRuntime(): Runtime {
  const r = useContext(RuntimeContext);
  if (!r) throw new Error('RuntimeContext missing');
  return r;
}

/** Strings, names and amounts in the current language and amount format. */
export function useText() {
  const lang = useUI(s => s.lang), mode = useUI(s => s.fmt);
  return {
    lang, mode,
    t: (k: string) => str(lang, k),
    nm: (o: Record<string, unknown> | null | undefined) => loc(o, 'name', lang),
    loc: (o: Record<string, unknown> | null | undefined, base: string) => loc(o, base, lang),
    fmt: (v: number | null | undefined, m?: AmountFormat) => fmt(v, m ?? mode),
  };
}

export function useNarrow() {
  const [narrow, setNarrow] = useState(() => window.innerWidth <= 760);
  useEffect(() => {
    const on = () => setNarrow(window.innerWidth <= 760);
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return narrow;
}

/** In-page link to a node: keeps a real href (copyable, middle-click) but navigates in the app. */
export function NodeLink({ id, children, flow, onNavigate }: { id: string; children: ReactNode; flow?: string; onNavigate?: () => void }) {
  const { c } = useRuntime();
  const click = (e: MouseEvent) => {
    e.preventDefault();
    onNavigate?.();
    if (flow) c.goFlow(flow); else c.go(id);
  };
  return <a href={'#node=' + encodeURIComponent(id)} data-flow={flow} onClick={click}>{children}</a>;
}

export function PageLinks({ pages, max }: { pages: number[]; max?: number }) {
  const ps = max ? pages.slice(0, max) : pages;
  return <>{ps.map((p, i) => <span key={p + ':' + i}>{i ? ', ' : ''}<a href={pdfHref(p)} target="_blank" rel="noopener">{p}</a></span>)}{max && pages.length > max ? '…' : ''}</>;
}

/** "▲ +9.9% (+€356.5M)"; for two negative values (a deficit) the change is in its size. */
export function Change({ v, p, short }: { v: number; p: number | null | undefined; short?: boolean }) {
  const { t, fmt } = useText();
  const ch = change(v, p);
  if (!ch) return null;
  const sign = ch.up ? '+' : '−';
  return <><span className="chg">{ch.up ? '▲' : '▼'} {sign}{ch.rel}%</span> ({sign}{fmt(ch.abs, short ? 'short' : undefined)}){ch.neg ? t(ch.up ? 'larger' : 'smaller') : ''}</>;
}
