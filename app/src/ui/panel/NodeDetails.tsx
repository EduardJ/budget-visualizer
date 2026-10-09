import { useMemo } from 'react';
import { catIds, cfg, colName, isIncome, isNegative } from '../../config';
import { nf0, pct } from '../../format';
import { altName, catName, flagName, kindName } from '../../i18n';
import type { BudgetNode, Flow } from '../../types';
import { Change, NodeLink, useRuntime, useText } from '../common';
import { CopyButton, Head } from './Head';
import { RefBlock } from './RefBlock';

const SHARE_KINDS = ['org', 'municipality', 'programme', 'subprogramme', 'project', 'dest', 'category', 'difference'];

/** A node: its figure and shares, its sources, then whichever of categories, funding, multi-year amounts, revenue,
 * projects and flows it has. */
export function NodeDetails({ id }: { id: string }) {
  const { g } = useRuntime(), { loc } = useText();
  const n = g.N.get(id)!;
  const note = loc(n, 'note');
  return <>
    <NodeHead n={n} />
    {note && <section><p className="note">{note}</p></section>}
    <Sources n={n} />
    {n.cats && Object.keys(n.cats).length > 0 && <Categories n={n} cats={n.cats} />}
    {n.sources && Object.keys(n.sources).length > 0 && <Funding sources={n.sources} />}
    {n.multi && <MultiYear n={n} multi={n.multi} />}
    {n.revenue && <Revenue lines={n.revenue} />}
    <Projects n={n} />
    <Flows n={n} />
  </>;
}

function shareOfParent(g: ReturnType<typeof useRuntime>['g'], n: BudgetNode) {
  if (n.stock || n.macro) return null;
  const par = n.parent ? g.N.get(n.parent) : undefined;
  if (par) return { p: par, v: Math.abs(n.amount) / Math.abs(par.amount) };
  const own = n.owner ? g.N.get(n.owner) : undefined;
  if (own) return { p: own, v: n.amount / own.amount };
  const inc = (g.IN.get(n.id) ?? []).filter(f => f.kind !== 'category' && f.kind !== 'source-link');
  const s = inc.length === 1 ? g.N.get(inc[0].source) : undefined;
  if (s && s.amount && Math.abs(n.amount) <= Math.abs(s.amount) * 1.0001) return { p: s, v: Math.abs(n.amount) / Math.abs(s.amount) };
  return null;
}

function NodeHead({ n }: { n: BudgetNode }) {
  const { g, c } = useRuntime(), { t, nm, fmt, lang } = useText();
  const budget = g.amountOf(cfg().totals.budget) ?? 1, inflows = g.amountOf(cfg().totals.inflows ?? cfg().totals.budget) ?? 1;
  const sp = shareOfParent(g, n);
  const share = n.macro ? t('macroNote') : n.stock ? t('stockNote')
    : isIncome(n.id) ? `${pct(Math.abs(n.amount) / inflows)} ${t('shareIn')}`
    : SHARE_KINDS.includes(n.kind) ? `${pct(Math.abs(n.amount) / budget)} ${t('shareTotal')}` : '';
  const src = cfg().sourceLang, name = nm(n), alt = altName(n, lang);
  const enTag = n.en_src && n.en_src !== 'proper noun' && lang !== src ? <span className="badge b-tr">{n.en_src === 'translated' ? t('translated') : src.toUpperCase()}</span> : null;
  const flags = (n.flags ?? []).map(f => <span key={f} className={'badge ' + (f === 'RECONCILIATION' ? 'b-rec' : 'b-amb')}>{flagName(f, lang)}</span>);
  return (
    <Head kind={<>{kindName(n.kind, lang)}{n.code ? ' · #' + n.code : ''} {flags}</>}
      title={<><h2>{name} {enTag}</h2>{alt && alt !== name && <p className="alt">{alt}</p>}</>}
      amount={<div className="amt">{fmt(isNegative(n.id) ? -n.amount : n.amount)}</div>}>
      <div className="shares">
        {sp && <>{pct(sp.v)} {t('shareParent')} (<NodeLink id={sp.p.id}>{nm(sp.p)}</NodeLink>)<br /></>}
        {share}
        {n.prev != null && <><br />{t('prevYear')}: {fmt(n.prev)} · <Change v={n.amount} p={n.prev} /></>}
      </div>
      <CopyButton onClick={() => c.cite(n)} />
    </Head>
  );
}

/** Where the figure is printed, plus the previous year's, the annex copies and a project's own and funding lines. */
function Sources({ n }: { n: BudgetNode }) {
  const { t, lang } = useText();
  const P = cfg().panel ?? {}, src = cfg().sourceLang;
  return (
    <section>
      <h3>{t('src')}</h3>
      <RefBlock rid={n.ref} col={n.refCol} />
      {n.prev_ref && n.prev_ref !== n.ref && <RefBlock rid={n.prev_ref} col={n.prevCol || P.prevCol} label={t('prevYear')} />}
      {(P.extraRefs ?? []).map(x => typeof n[x.field] === 'string' && <RefBlock key={x.field} rid={n[x.field] as string} col={x.col} label={x.label[lang] ?? x.label[src]} />)}
      {n.head_ref && n.head_ref !== n.ref && <RefBlock rid={n.head_ref} label={t('projectLine')} />}
      {(n.src_refs ?? []).filter(r => r !== n.ref).map(r => <RefBlock key={r} rid={r} col={P.sourceRefCol} />)}
    </section>
  );
}

function Categories({ n, cats }: { n: BudgetNode; cats: Record<string, number> }) {
  const { g } = useRuntime(), { t, fmt, lang } = useText();
  const tot = Object.values(cats).reduce((a, v) => a + v, 0) || 1;
  return (
    <section>
      <h3>{t('cats_h')}</h3>
      <div className="catbar">{catIds().filter(k => cats[k] > 0).map(k => <i key={k} style={{ width: `${(100 * cats[k]) / tot}%`, background: `var(--c-${k})` }} title={catName(k, lang)} />)}</div>
      <table className="kv"><tbody>{catIds().filter(k => cats[k]).map(k => {
        const fl = (g.OUT.get(n.id) ?? []).find(f => f.target === 'cat:' + k);
        return <tr key={k}><td><span className="sw" style={{ background: `var(--c-${k})` }} /> {fl ? <NodeLink id={n.id} flow={fl.id}>{catName(k, lang)}</NodeLink> : catName(k, lang)}</td><td>{fmt(cats[k])} · {pct(cats[k] / tot)}</td></tr>;
      })}</tbody></table>
      {!!n.staff && <p className="note">{t('staff')}: <b>{nf0().format(n.staff)}</b> ({n.ref && g.REFS[n.ref] ? g.REFS[n.ref].table : ''})</p>}
    </section>
  );
}

function Funding({ sources }: { sources: NonNullable<BudgetNode['sources']> }) {
  const { t, fmt, loc } = useText();
  return <section><h3>{t('sources_h')}</h3><table className="kv"><tbody>{Object.entries(sources).map(([k, s]) => <tr key={k}><td>{loc(s, 'label')}</td><td>{fmt(s.amount)}</td></tr>)}</tbody></table></section>;
}

function MultiYear({ n, multi }: { n: BudgetNode; multi: Record<string, number> }) {
  const { g } = useRuntime(), { t, fmt, lang } = useText();
  return (
    <section>
      <h3>{t('multi')}</h3>
      <table className="kv"><tbody>{(cfg().panel?.multiYear ?? Object.keys(multi)).map(k => <tr key={k}><td>{colName(k)}</td><td>{fmt(multi[k])}</td></tr>)}</tbody></table>
      <p className="note">{t('owner')}: {n.owner && <NodeLink id={n.owner}>{g.nameOf(n.owner, lang)}</NodeLink>}<br />{n.sub_label || ''}<br />{n.dates ? n.dates + ' · ' : ''}{(n.fund ?? []).join(', ')}{n.prop_code ? ' · ' + n.prop_code : ''}</p>
    </section>
  );
}

function Revenue({ lines }: { lines: NonNullable<BudgetNode['revenue']> }) {
  const { t, fmt } = useText();
  return (
    <section>
      <h3>{t('rev_h')}</h3>
      <table className="kv"><tbody>{lines.filter(r => r.amount).map((r, i) => <tr key={i}><td>{r.label}</td><td>{fmt(r.amount)}</td></tr>)}</tbody></table>
      <RefBlock rid={lines[0].ref} col={cfg().panel?.revenueCol} />
    </section>
  );
}

/** Capital projects run by an organisation shown as a card. */
function Projects({ n }: { n: BudgetNode }) {
  const { g, c } = useRuntime(), { t, nm, fmt } = useText();
  const projs = useMemo(() => cfg().tabs.some(tb => tb.layout === 'cards' && tb.kind === n.kind)
    ? [...g.N.values()].filter(p => p.kind === 'project' && p.owner === n.id && p.amount > 0).sort((a, b) => b.amount - a.amount) : [], [g, n]);
  if (!projs.length) return null;
  return (
    <section>
      <h3>{t('projects')} ({projs.length})</h3>
      <ul className="fl">{projs.slice(0, 25).map(p => (
        <li key={p.id}><button data-node={p.id} onClick={() => c.go(p.id)}><span>{nm(p)}</span><b>{fmt(p.amount)}</b><small>{p.table} · {t('page')} {p.head_ref && g.REFS[p.head_ref] ? g.REFS[p.head_ref].page : ''}</small></button></li>
      ))}</ul>
      {projs.length > 25 && <p className="note">+{projs.length - 25}</p>}
    </section>
  );
}

function Flows({ n }: { n: BudgetNode }) {
  const { g } = useRuntime(), { t } = useText();
  const ins = g.IN.get(n.id) ?? [], outs = (g.OUT.get(n.id) ?? []).filter(f => f.kind !== 'project').sort((a, b) => b.amount - a.amount);
  return <>
    {ins.length > 0 && <section><h3>{t('inflows')} ({ins.length})</h3><ul className="fl">{ins.slice(0, 40).map(f => <FlowItem key={f.id} f={f} dir="in" />)}</ul></section>}
    {outs.length > 0 && <section>
      <h3>{t('outflows')} ({outs.length})</h3>
      <ul className="fl">{outs.slice(0, 60).map(f => <FlowItem key={f.id} f={f} dir="out" />)}</ul>
      {outs.length > 60 && <p className="note">+{outs.length - 60}</p>}
    </section>}
  </>;
}

function FlowItem({ f, dir }: { f: Flow; dir: 'in' | 'out' }) {
  const { g, c } = useRuntime(), { t, nm, fmt, lang } = useText();
  const o = g.N.get(dir === 'in' ? f.source : f.target);
  if (!o) return null;
  const how = f.kind === 'source-link' ? ` · ${t('attributed')}` : f.kind === 'category' ? ` · ${catName(f.col ?? '', lang)}` : '';
  return (
    <li><button data-flow={f.id} data-node={o.id} onClick={() => c.go(o.id)}>
      <span>{nm(o)}</span><b>{fmt(f.amount)}</b><small>{t(dir === 'in' ? 'flowFrom' : 'flowTo')} {kindName(o.kind, lang)}{how}</small>
    </button></li>
  );
}
