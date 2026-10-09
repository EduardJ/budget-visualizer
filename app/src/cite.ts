import type { Graph } from './data/graph';
import { fmt } from './format';
import { loc, str } from './i18n';
import type { BudgetNode, Flow, Ref } from './types';

// Citations copied from the panel: the amount, where it is printed, and the law.

const pages = (r: Ref | undefined) => (r ? (r.pages || [r.page]).join(', ') : '');

export function citeNode(n: BudgetNode, g: Graph, lang: string): string {
  const t = (k: string) => str(lang, k), r = n.ref ? g.REFS[n.ref] : undefined, col = n.refCol ?? '';
  const orig = r?.values?.[col] ? `, ${t('orig')}: ${r.values[col]}` : '';
  return `${loc(n, 'name', lang)} — ${fmt(n.amount, 'full')} (${r?.table || ''}, ${t('page')} ${pages(r)}, ${t('row')}: "${r?.row || r?.original_label || ''}"${orig}). ${g.D.meta.law}, ${g.D.meta.gazette}.`;
}

export function citeFlow(f: Flow, g: Graph, lang: string): string {
  const t = (k: string) => str(lang, k), r = f.ref ? g.REFS[f.ref] : undefined;
  return `${g.nameOf(f.source, lang)} → ${g.nameOf(f.target, lang)} — ${fmt(f.amount, 'full')} (${r?.table}, ${t('page')} ${pages(r)}, ${t('row')}: "${r?.row || r?.original_label}"). ${g.D.meta.law}.`;
}

/** Clipboard API where allowed (secure contexts), a hidden textarea elsewhere (file://, sandboxed iframes). */
export function copyText(s: string): Promise<void> {
  const fallback = () => {
    const ta = document.createElement('textarea');
    ta.value = s; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch { /* nothing else to try */ }
    ta.remove();
  };
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(s).catch(fallback);
  fallback();
  return Promise.resolve();
}
