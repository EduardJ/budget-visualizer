import { cfg } from './config';
import { fold } from './format';
import type { SearchRow } from './types';

export interface SearchHit { id: string; amount: number; kind: string; table: string; pages: (number | null)[]; [name: string]: unknown }

/** Search by name (accent-insensitive, every word must match), by amount ("1,194,770,851", "1.2M", "€5M") or by page ("p 45"). */
export function createSearch(rows: SearchRow[]) {
  const nameKey = 'name_' + cfg().sourceLang;
  const IDX = rows.map(r => ({
    n: { id: r[0], [nameKey]: r[1], name_en: r[2], amount: r[3], kind: r[4], table: r[5], pages: r[6] } as SearchHit,
    s: fold(r[1] + ' ' + r[2] + ' ' + r[8]),
    p: r[6] || [],
  }));
  const byAmount = (a: { n: SearchHit }, b: { n: SearchHit }) => Math.abs(b.n.amount) - Math.abs(a.n.amount);
  return (q: string): SearchHit[] => {
    q = q.trim();
    if (!q) return [];
    const pm = q.match(/^(?:p|f|faqe|page)\.?\s*(\d{1,3})$/i);
    if (pm) { const p = +pm[1]; return IDX.filter(x => x.p.includes(p)).sort(byAmount).slice(0, 40).map(x => x.n); }
    const am = /\d/.test(q) && !/[a-zë]{3,}/i.test(q) ? parseAmount(q) : null;
    if (am) {
      const d = (x: { n: SearchHit }) => Math.abs(Math.abs(x.n.amount) - am.v);
      return IDX.filter(x => d(x) <= am.tol).sort((a, b) => d(a) - d(b)).slice(0, 40).map(x => x.n);
    }
    const words = fold(q).split(/\s+/).filter(Boolean);
    return IDX.filter(x => words.every(w => x.s.includes(w))).sort(byAmount).slice(0, 40).map(x => x.n);
  };
}

/** "1,194,770,851" matches to the euro; "1.2M" or "€5M" match within 5%. */
function parseAmount(q: string) {
  const m = q.replace(/[€\s]/g, '').match(/^([\d.,]+)(k|m|b)?$/i);
  if (!m) return null;
  let s = m[1];
  const mult = ({ k: 1e3, m: 1e6, b: 1e9 } as Record<string, number>)[(m[2] || '').toLowerCase()] || 1;
  s = mult === 1 ? s.replace(/,/g, '') : s.replace(/,/g, '.');
  const v = parseFloat(s);
  if (isNaN(v)) return null;
  return { v: v * mult, tol: mult === 1 ? Math.max(0.5, v * 0.0005) : v * mult * 0.05 };
}
