import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import type { BudgetData, BudgetNode, Chunk, CoreData, DatasetConfig, Dict, Flow, Ref, SearchRow } from '../app/src/types.ts';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const BUILTIN = JSON.parse(readFileSync(join(ROOT, 'app/src/strings.json'), 'utf8')) as Record<string, Record<string, unknown>>;
const isBuiltin = (lang: string, key: string) => BUILTIN[lang]?.[key] != null;

export interface Dataset { dir: string; config: DatasetConfig; data: BudgetData; snippets: Map<string, Buffer>; pdf: string }

/** DATASET_DIR (a folder anywhere), or DATASET (a folder name under datasets/), or the only dataset there is.
 * The pipeline's BUDGET_DATASET / BUDGET_DATASET_DIR are honoured too, so one variable drives both halves. */
export function datasetDir(): string {
  const env = process.env, dir = env.DATASET_DIR || env.BUDGET_DATASET_DIR, id = env.DATASET || env.BUDGET_DATASET;
  if (dir) return resolve(dir);
  const base = join(ROOT, 'datasets');
  if (id) return join(base, id);
  const all = existsSync(base) ? readdirSync(base).filter(d => existsSync(join(base, d, 'dataset.json'))) : [];
  if (all.length === 1) return join(base, all[0]);
  throw new Error(`Set DATASET to one of: ${all.join(', ') || '(no datasets found under datasets/)'}`);
}

const refNum = (r: string) => +r.slice(1);

export function loadDataset(dir: string): Dataset {
  const read = (f: string) => {
    const p = join(dir, f);
    if (!existsSync(p)) throw new Error(`${p} is missing`);
    return readFileSync(p, 'utf8');
  };
  const config = JSON.parse(read('dataset.json')) as DatasetConfig;
  const data = JSON.parse(read('data.json')) as BudgetData;
  const snippets = new Map<string, Buffer>();
  const sdir = join(dir, 'snippets');
  if (existsSync(sdir)) {
    for (const f of readdirSync(sdir).filter(f => /^r\d+\.jpg$/.test(f)).sort((a, b) => refNum(a) - refNum(b))) snippets.set(f.slice(0, -4), readFileSync(join(sdir, f)));
  }
  return { dir, config, data, snippets, pdf: join(dir, config.pdf) };
}

// ---- validation: the schema, then what a schema cannot express ----

interface Report { errors: string[]; warnings: string[] }

export function validate(ds: Dataset): Report {
  const r: Report = { errors: schemaErrors(ds), warnings: [] };
  if (r.errors.length) return r;
  references(ds, r);
  translations(ds, r);
  presentation(ds, r);
  return r;
}

function schemaErrors(ds: Dataset): string[] {
  const ajv = new Ajv2020({ allErrors: true, strict: false }), out: string[] = [];
  for (const [file, schema, value] of [['dataset.json', 'dataset.schema.json', ds.config], ['data.json', 'data.schema.json', ds.data]] as const) {
    const check = ajv.compile(JSON.parse(readFileSync(join(ROOT, 'schema', schema), 'utf8')));
    if (!check(value)) for (const e of (check.errors ?? []).slice(0, 25)) out.push(`${file}${e.instancePath || ''}: ${e.message}`);
  }
  return out;
}

/** Every ref, node and flow that something points to exists (rule 2: every number has a source). */
function references({ config: C, data: D, pdf, dir }: Dataset, { errors, warnings }: Report) {
  if (!existsSync(pdf)) errors.push(`dataset.json pdf: ${C.pdf} not found in ${dir}`);
  if (D.meta.pdf !== C.pdf) warnings.push(`data.json meta.pdf (${D.meta.pdf}) differs from dataset.json pdf (${C.pdf}); the viewer links to ${C.pdf}`);
  const N = new Map(D.nodes.map(n => [n.id, n])), F = new Map(D.flows.map(f => [f.id, f]));
  if (N.size !== D.nodes.length) errors.push('data.json: duplicate node ids');
  if (F.size !== D.flows.length) errors.push('data.json: duplicate flow ids');
  const ref = (where: string, r: unknown) => { if (typeof r === 'string' && !D.refs[r]) errors.push(`${where}: ref ${r} is not in refs`); };
  const node = (where: string, id: unknown) => { if (typeof id === 'string' && !N.has(id)) errors.push(`${where}: node ${id} does not exist`); };
  const extra = (C.panel?.extraRefs ?? []).map(x => x.field);
  for (const n of D.nodes) {
    const w = `node ${n.id}`;
    for (const k of ['ref', 'prev_ref', 'head_ref', ...extra]) ref(w, n[k]);
    for (const r of n.src_refs ?? []) ref(w, r);
    for (const r of n.revenue ?? []) ref(w, r.ref);
    for (const s of Object.values(n.sources ?? {})) ref(w, s.ref);
    for (const k of ['parent', 'owner', 'anchor']) node(w, n[k]);
  }
  for (const f of D.flows) { ref(`flow ${f.id}`, f.ref); node(`flow ${f.id} source`, f.source); node(`flow ${f.id} target`, f.target); }
  for (const k of D.kpis) { ref(`kpi ${k.key}`, k.ref); ref(`kpi ${k.key}`, k.prev_ref); node(`kpi ${k.key}`, k.node); }
  for (const t of D.tours) for (const [i, s] of t.steps.entries()) {
    node(`tour ${t.id} step ${i + 1}`, s.node);
    if (s.flow && !F.has(s.flow)) errors.push(`tour ${t.id} step ${i + 1}: flow ${s.flow} does not exist`);
  }
  for (const f of D.findings) node(`finding "${f.title.slice(0, 40)}"`, f.node);
  for (const [k, id] of Object.entries(C.totals)) node(`dataset.json totals.${k}`, id);
  for (const t of C.tabs) if (t.layout === 'sankey') for (const col of t.columns) for (const id of col.nodes) if (!N.has(id)) warnings.push(`tab ${t.id}: column node ${id} does not exist (skipped)`);
}

/** Every user-facing text in every UI language (rule 4). English is the unsuffixed field of checks and findings. */
function translations({ config: C, data: D }: Dataset, { errors }: Report) {
  const others = C.langs.filter(l => l !== 'en');
  const need = (what: string, o: Record<string, unknown>, base: string, langs: string[], optional = false) => {
    if (optional && !o[base] && !o[base + '_en']) return;
    for (const l of langs) if (!o[`${base}_${l}`]) errors.push(`${what}: no ${base}_${l}`);
  };
  for (const n of D.nodes) if (!n['name_' + C.sourceLang]) errors.push(`node ${n.id}: no name_${C.sourceLang}`);
  for (const c of D.checks) { need(`check ${c.id}`, c, 'title', others); need(`check ${c.id}`, c, 'note', others, true); }
  for (const f of D.findings) { const w = `finding "${f.title.slice(0, 40)}"`; need(w, f, 'title', others); need(w, f, 'type', others, true); }
  for (const t of D.tours) { need(`tour ${t.id}`, t, 'title', C.langs); for (const s of t.steps) need(`tour ${t.id} step`, s, 'text', C.langs); }
  for (const k of D.kpis) need(`kpi ${k.key}`, k, 'label', C.langs);
}

/** dataset.json fits the data: tabs, chunks, categories, and a string for every key it uses. */
function presentation({ config: C, data: D }: Dataset, { errors, warnings }: Report) {
  if (new Set(C.tabs.map(t => t.id)).size !== C.tabs.length) errors.push('dataset.json: duplicate tab ids');
  const kinds = new Set(D.nodes.map(n => n.kind)), sections = new Set(D.nodes.map(n => n.section));
  for (const k of D.kpis) if (!C.tabs.some(t => t.id === k.tab)) errors.push(`kpi ${k.key}: tab ${k.tab} is not in dataset.json tabs`);
  const keys = new Set<string>(['title', 'sub', ...(C.levels ?? []).map(l => l.label)]);
  for (const t of C.tabs) {
    keys.add(t.title); keys.add('tab_' + t.id);
    if (t.chunk && !(C.chunks ?? {})[t.chunk]) errors.push(`dataset.json tab ${t.id}: chunk ${t.chunk} is not in chunks`);
    if (t.layout === 'sankey') for (const col of t.columns) keys.add(col.header);
    if ((t.layout === 'cards' || t.layout === 'ranking') && !kinds.has(t.kind)) errors.push(`dataset.json tab ${t.id}: no nodes of kind ${t.kind}`);
    if (t.layout === 'cards') { if (t.note) keys.add(t.note); for (const o of t.sort ?? []) keys.add(o.label); }
  }
  for (const [chunk, secs] of Object.entries(C.chunks ?? {})) for (const s of secs) if (!sections.has(s)) warnings.push(`chunk ${chunk}: no nodes in section ${s}`);
  const catIds = new Set(C.categories.map(c => c.id));
  for (const n of D.nodes) {
    const bad = Object.keys(n.cats ?? {}).find(k => !catIds.has(k));
    if (bad) errors.push(`node ${n.id}: category ${bad} is not in dataset.json categories`);
  }
  for (const l of C.langs) {
    for (const k of keys) if (C.strings[l]?.[k] == null && !isBuiltin(l, k)) errors.push(`dataset.json strings.${l}: missing "${k}"`);
    for (const c of C.categories) if (!c.name[l]) errors.push(`dataset.json category ${c.id}: no name in ${l}`);
    if (!BUILTIN[l]) warnings.push(`language ${l}: built-in interface text exists only for ${Object.keys(BUILTIN).join(' and ')}; add it to app/src/strings.json or override every key in dataset.json strings`);
    if (!C.assumptions?.[l]?.length) warnings.push(`dataset.json assumptions: none in ${l}`);
  }
}

// ---- bundling: one core chunk parsed at start, the rest on first use ----

export interface Bundle { core: CoreData; chunks: Dict<Chunk> }

const REF = /^r\d+$/;
function refsIn(o: unknown, out: Set<string>) {
  if (typeof o === 'string') { if (REF.test(o)) out.add(o); }
  else if (Array.isArray(o)) for (const v of o) refsIn(v, out);
  else if (o && typeof o === 'object') for (const v of Object.values(o)) refsIn(v, out);
  return out;
}

export function bundle(ds: Dataset): Bundle {
  const { config: C, data: D } = ds;
  // nodes drawn on a sankey tab always travel with the core chunk
  const sankey = new Set(C.tabs.flatMap(t => (t.layout === 'sankey' ? t.columns.flatMap(c => c.nodes) : [])));
  const bySection = new Map<string, string>();
  for (const [chunk, secs] of Object.entries(C.chunks ?? {})) for (const s of secs) bySection.set(s, chunk);
  const NC = new Map(D.nodes.map(n => [n.id, sankey.has(n.id) ? 'core' : bySection.get(n.section ?? '') ?? 'core']));
  const chunkOf = (id: string) => NC.get(id) ?? 'core';
  const flowChunk = (f: Flow) => (chunkOf(f.target) !== 'core' ? chunkOf(f.target) : chunkOf(f.source));
  const names = ['core', ...Object.keys(C.chunks ?? {})];
  const parts: Dict<{ nodes: BudgetNode[]; flows: Flow[]; refs: Dict<Ref> }> = Object.fromEntries(names.map(k => [k, { nodes: [], flows: [], refs: {} }]));
  for (const n of D.nodes) parts[chunkOf(n.id)].nodes.push(n);
  for (const f of D.flows) parts[flowChunk(f)].flows.push(f);
  for (const [k, c] of Object.entries(parts)) {
    const rs = new Set<string>();
    for (const o of [...c.nodes, ...c.flows]) refsIn(o, rs);
    if (k === 'core') for (const o of [...D.kpis, ...D.checks, ...D.findings]) refsIn(o, rs);
    for (const r of [...rs].sort((a, b) => refNum(a) - refNum(b))) if (D.refs[r]) c.refs[r] = D.refs[r];
  }
  // which other chunks a node's details panel needs (flows that live elsewhere, owned projects)
  const need = new Map<string, Set<string>>();
  const add = (id: string, k: string) => { const s = need.get(id); if (s) s.add(k); else need.set(id, new Set([k])); };
  for (const f of D.flows) { const fc = flowChunk(f); for (const end of [f.source, f.target]) if (fc !== chunkOf(end)) add(end, fc); }
  for (const n of D.nodes) if (n.owner && chunkOf(n.id) !== chunkOf(n.owner)) add(n.owner, chunkOf(n.id));
  const nameKey = 'name_' + C.sourceLang;
  const search: SearchRow[] = D.nodes.map(n => {
    const r = n.ref ? D.refs[n.ref] : undefined;
    return [n.id, String(n[nameKey] ?? ''), String(n.name_en || ''), n.amount, n.kind, r?.table ?? '', r?.pages ?? [r?.page ?? null], chunkOf(n.id), String(n.code ?? '')];
  });
  const core: CoreData = {
    meta: { ...D.meta, pdf: C.pdf }, sources: D.sources ?? [], kpis: D.kpis, checks: D.checks, findings: D.findings, tours: D.tours, summary: D.summary ?? {},
    ...parts.core,
    need: Object.fromEntries([...need].map(([k, v]) => [k, [...v].sort()])),
    flowChunk: Object.fromEntries(D.flows.filter(f => flowChunk(f) !== 'core').map(f => [f.id, flowChunk(f)])),
    search,
  };
  const chunks = Object.fromEntries(names.filter(k => k !== 'core').map(k => [k, parts[k]]));
  return { core, chunks };
}

export const jsonForHtml = (v: unknown) => JSON.stringify(v).replace(/<\//g, '<\\/');
