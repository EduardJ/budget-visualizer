import { cfg } from './config';
import BUILTIN from './strings.json';

type Strings = Record<string, string | string[]>;

// Built-in interface text lives in strings.json (read by the build's validator too). A dataset adds its own keys
// (title, section and tab names, notes that cite its tables) and may override any of them in dataset.json "strings".
// A new UI language needs a full set there or in the dataset.
const UI = BUILTIN as Record<string, Strings>;

export function str(lang: string, key: string): string {
  const v = lookup(lang, key);
  return Array.isArray(v) ? v.join(' ') : v ?? key;
}

export function strList(lang: string, key: string): string[] {
  const v = lookup(lang, key);
  return Array.isArray(v) ? v : v != null ? [v] : [];
}

function lookup(lang: string, key: string) {
  return cfg().strings[lang]?.[key] ?? UI[lang]?.[key] ?? UI.en[key];
}

export function hasString(lang: string, key: string) {
  return lookup(lang, key) != null;
}

export const docTitle = (lang: string) => str(lang, hasString(lang, 'documentTitle') ? 'documentTitle' : 'title');

export const fill = (s: string, vars: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ''));


/** Localised field: name_<lang>, falling back to English, the unsuffixed field, then the document language. */
export function loc(o: Record<string, unknown> | null | undefined, base: string, lang: string): string {
  if (!o) return '';
  const src = cfg().sourceLang;
  for (const k of [`${base}_${lang}`, `${base}_en`, base, `${base}_${src}`]) {
    const v = o[k];
    if (typeof v === 'string' && v) return v;
  }
  return '';
}

/** The name in the other UI language, shown under the main name. */
export function altName(o: Record<string, unknown>, lang: string): string {
  const src = cfg().sourceLang;
  if (lang !== src) return String(o[`name_${src}`] ?? '');
  const other = cfg().langs.find(l => l !== src);
  return other ? String(o[`name_${other}`] || '') : '';
}

export function catName(id: string, lang: string): string {
  const c = cfg().categories.find(c => c.id === id);
  return c ? c.name[lang] ?? c.name[cfg().sourceLang] ?? id : id;
}

export function kindName(kind: string, lang: string): string {
  return hasString(lang, 'kind_' + kind) ? str(lang, 'kind_' + kind) : kind;
}

export function flagName(flag: string, lang: string): string {
  const own = cfg().flags?.[flag];
  if (own) return own[lang] ?? own[cfg().sourceLang] ?? flag;
  return hasString(lang, 'flag_' + flag) ? str(lang, 'flag_' + flag) : flag;
}
