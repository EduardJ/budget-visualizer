import { cfg } from './config';

export type AmountFormat = 'full' | 'short';

let nf: Intl.NumberFormat | null = null;
export const nf0 = () => (nf ??= new Intl.NumberFormat(cfg().numberLocale ?? 'en-US', { maximumFractionDigits: 0 }));

export function fmt(v: number | null | undefined, mode: AmountFormat): string {
  if (v == null || isNaN(v)) return '–';
  const neg = v < 0, a = Math.abs(v);
  let s: string;
  if (mode === 'short') {
    if (a >= 1e9) s = (a / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
    else if (a >= 1e6) s = (a / 1e6).toFixed(a >= 1e8 ? 0 : 1).replace(/\.0$/, '') + 'M';
    else if (a >= 1e3) s = (a / 1e3).toFixed(0) + 'K';
    else s = nf0().format(a);
  } else s = nf0().format(Math.round(a));
  return (neg ? '−' : '') + (cfg().currency ?? '€') + s;
}

export const pct = (v: number) => (v * 100 >= 10 ? (v * 100).toFixed(1) : v * 100 >= 1 ? (v * 100).toFixed(2) : (v * 100).toFixed(3)).replace(/\.?0+$/, '') + '%';

/** Lower-case and strip diacritics so "Prishtinë" matches "prishtine". */
export const fold = (s: unknown) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ë/g, 'e').replace(/ç/g, 'c');

/** Change from the previous year; for two negative values (a deficit) the change is in its size. */
export function change(v: number, p: number | null | undefined) {
  if (p == null || !p) return null;
  const neg = v < 0 && p < 0, a = neg ? -v : v, b = neg ? -p : p;
  const d = a - b, r = d / Math.abs(b);
  return { up: d >= 0, rel: Math.abs(r * 100).toFixed(1), abs: Math.abs(d), neg };
}
