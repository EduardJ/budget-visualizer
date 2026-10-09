import { cfg } from './config';
import { fmt, nf0, type AmountFormat } from './format';
import { str } from './i18n';
import type { Check, Finding } from './types';

export type CheckClass = 'error' | 'rounding' | 'pass';

export const clsOf = (c: Check): CheckClass => (c.status === 'pass' ? 'pass' : c.cls || 'error');
export const findingCls = (f: Finding): 'error' | 'rounding' | null => (f.type === 'mismatch' ? f.cls || 'error' : null);
export const CLSCOL: Record<CheckClass, string> = { error: '#b3261e', rounding: '#a86a00', pass: '#2e7d4f' };
export const clsName = (k: CheckClass, lang: string) => str(lang, 'cls_' + k);
export const clsExplain = (k: CheckClass, lang: string) => str(lang, 'explain_' + k);

/** A check value in the unit the check is about. */
export function ckv(c: Check, v: number | null | undefined, mode: AmountFormat): string {
  if (v == null) return '–';
  if (c.kind === 'count') return nf0().format(v);
  if (c.unit === '%' || c.kind === 'percent') return Math.round(v * 1000) / 1000 + '%';
  if (c.kind === 'claim' && c.unit === '€ million') return (cfg().currency ?? '€') + v + 'M';
  if (c.kind === 'law' && Math.abs(v) <= 1) return String(v);
  return fmt(v, mode);
}

export const findingDiff = (f: Finding, mode: AmountFormat) => (f.unit === 'percent' ? f.diff + ' pp' : fmt(f.diff, mode));
