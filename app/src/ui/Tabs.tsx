import { cfg, tabById } from '../config';
import { clsOf } from '../checks';
import type { HeadlineTarget } from '../controller';
import type { Graph } from '../data/graph';
import { nf0 } from '../format';
import { fill, loc } from '../i18n';
import { useUI } from '../state/store';
import type { CardsTab, Kpi } from '../types';
import { Change, useNarrow, useRuntime, useText } from './common';

export function Tabs() {
  const { c } = useRuntime(), { t } = useText();
  const tab = useUI(s => s.tab), sorts = useUI(s => s.sorts);
  const cur = tabById(tab);
  const sort = cur?.layout === 'cards' ? (cur as CardsTab).sort : undefined;
  return (
    <nav id="tabs" role="tablist" aria-label="Views">
      {cfg().tabs.map(tb => <button key={tb.id} role="tab" data-tab={tb.id} aria-selected={tb.id === tab} onClick={() => c.pickTab(tb.id)}>{t('tab_' + tb.id)}</button>)}
      {sort && (
        <label className="tabsort">{t('sort')}{' '}
          <select id="tabsort" value={sorts[tab] ?? sort[0].id} onChange={e => c.setSort(tab, e.target.value)}>
            {sort.map(o => <option key={o.id} value={o.id}>{t(o.label)}</option>)}
          </select>
        </label>
      )}
    </nav>
  );
}

interface Headline { label: string; text: string; sub?: string; bad?: boolean; prev?: { value: number; prev: number }; target: HeadlineTarget }

/** Headline figures of the checks tab, counted from the checks themselves. */
function checkHeadlines(g: Graph, t: (k: string) => string, fmt: (v: number) => string, lang: string): Headline[] {
  const { checks, findings } = g.D;
  const n = (k: string) => checks.filter(c => clsOf(c) === k).length;
  const rows = (k: string) => findings.filter(f => f.type === 'mismatch' && (f.cls || 'error') === k).length;
  const money = checks.filter(c => clsOf(c) === 'error' && c.kind !== 'count' && c.unit !== '%' && c.kind !== 'claim').sort((a, b) => Math.abs(b.diff ?? 0) - Math.abs(a.diff ?? 0));
  const gap = money[0];
  return [
    { label: t('kpi_error'), text: String(n('error')), bad: true, sub: fill(t('kpi_error_sub'), { n: rows('error') }), target: { kind: 'recon', filter: 'error' } },
    { label: t('kpi_rounding'), text: String(n('rounding')), sub: fill(t('kpi_rounding_sub'), { n: rows('rounding') }), target: { kind: 'recon', filter: 'rounding' } },
    { label: t('kpi_pass'), text: `${n('pass')} / ${checks.length}`, target: { kind: 'recon', filter: 'pass' } },
    gap ? { label: t('kpi_gap'), text: fmt(gap.diff ?? 0), sub: loc(gap, 'title', lang), target: { kind: 'check', check: gap } }
        : { label: t('kpi_gap'), text: '–', target: { kind: 'recon', filter: 'error' } },
    { label: t('kpi_notes'), text: String(findings.filter(f => f.type !== 'mismatch').length), target: { kind: 'recon', filter: 'note' } },
  ];
}

const dataHeadline = (k: Kpi, lang: string, text: string): Headline => ({
  label: loc(k, 'label', lang), sub: loc(k, 'sub', lang), text, target: { kind: 'kpi', kpi: k },
  prev: k.prev != null ? { value: k.value, prev: k.prev } : undefined,
});

export function Kpis() {
  const { g, c } = useRuntime(), { t, fmt, lang } = useText();
  const tab = useUI(s => s.tab);
  const narrow = useNarrow(); // phones get rounded values so they fit; the panel shows the full figure
  const items = tabById(tab)?.layout === 'checks'
    ? checkHeadlines(g, t, v => fmt(v), lang)
    : g.D.kpis.filter(k => k.tab === tab).map(k => dataHeadline(k, lang, k.unit === 'count' ? nf0().format(k.value) : fmt(k.value, narrow ? 'short' : undefined)));
  return (
    <div id="kpis" aria-label="Headline figures">
      {items.map((h, i) => (
        <button key={tab + i} className={'kpi' + (h.bad ? ' bad' : '')} data-k={i} onClick={() => c.openHeadline(h.target)}>
          <span className="kl">{h.label}</span><b>{h.text}</b>
          {h.prev && <span className="kd"><Change v={h.prev.value} p={h.prev.prev} short /> {t('vs')} {t('prevYear')}</span>}
          {h.sub && <span className="ks">{h.sub}</span>}
        </button>
      ))}
    </div>
  );
}
