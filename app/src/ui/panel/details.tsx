import { cfg } from '../../config';
import { ckv, clsExplain, clsName, clsOf, CLSCOL, findingCls } from '../../checks';
import { nf0, pct } from '../../format';
import type { Check, Finding, Kpi } from '../../types';
import { Change, PageLinks, useRuntime, useText } from '../common';
import { CopyButton, Head } from './Head';
import { RefBlock } from './RefBlock';

export function FlowDetails({ id }: { id: string }) {
  const { g, c } = useRuntime(), { t, nm, fmt, loc } = useText();
  const f = g.F.get(id)!, a = g.N.get(f.source), b = g.N.get(f.target);
  const ps = a && a.amount ? Math.abs(f.amount / a.amount) : null;
  const note = loc(f, 'note');
  return <>
    <Head kind={<>{t('flowKind')}{f.kind !== 'hard' ? ' · ' + (f.kind === 'source-link' ? t('attributed') : f.kind) : ''}</>}
      title={<h2>{nm(a)} → {nm(b)}</h2>} amount={<div className="amt">{fmt(f.amount)}</div>}>
      <div className="shares">{ps != null && <>{pct(ps)} {t('shareParent')} ({nm(a)})<br /></>}{pct(f.amount / (g.amountOf(cfg().totals.budget) ?? 1))} {t('shareTotal')}</div>
      <CopyButton onClick={() => c.citeFlow(id)} />
    </Head>
    {note && <section><p className="note">{note}</p></section>}
    <section><h3>{t('src')}</h3><RefBlock rid={f.ref} col={f.col} /></section>
    <section><ul className="fl">
      {a && <li><button data-node={a.id} onClick={() => c.go(a.id)}><span>{t('flowFrom')}: {nm(a)}</span><b>{fmt(a.amount)}</b></button></li>}
      {b && <li><button data-node={b.id} onClick={() => c.go(b.id)}><span>{t('flowTo')}: {nm(b)}</span><b>{fmt(b.amount)}</b></button></li>}
    </ul></section>
  </>;
}

export function CheckDetails({ c: chk }: { c: Check }) {
  const { g } = useRuntime(), { t, lang, mode, loc } = useText();
  const k = clsOf(chk), note = loc(chk, 'note');
  const v = (x: number | null | undefined) => ckv(chk, x, mode);
  return <>
    <Head kind={<>{t('checks')} · <span style={{ color: CLSCOL[k], fontWeight: 600 }}>{clsName(k, lang)}</span>{chk.group ? ' · ' + chk.group : ''}</>}
      title={<h2>{loc(chk, 'title')}</h2>} amount={<div className="amt">{v(chk.kind === 'count' ? chk.actual : chk.diff)}</div>} />
    <section>
      <table className="kv"><tbody>
        <tr><td>{t('expected')}</td><td>{v(chk.expected)}</td></tr>
        <tr><td>{t('actual')}</td><td>{v(chk.actual)}</td></tr>
        <tr><td>{t('diff')}</td><td>{v(chk.diff)}</td></tr>
        <tr><td>{t('cls')}</td><td style={{ color: CLSCOL[k] }}>{clsName(k, lang)}</td></tr>
        <tr><td>{t('pages')}</td><td><PageLinks pages={chk.pages} /></td></tr>
      </tbody></table>
      {note && <p className="note">{note}</p>}
      <p className="note">{clsExplain(k, lang)}</p>
    </section>
    {(chk.refs ?? []).filter(r => g.REFS[r]).slice(0, 6).map(r => <RefBlock key={r} rid={r} col={cfg().panel?.checkRefCol} />)}
  </>;
}

export function FindingDetails({ f }: { f: Finding }) {
  const { g, c } = useRuntime(), { t, fmt, lang, loc } = useText();
  const fk = findingCls(f);
  return <>
    <Head kind={<>{t('findings')} · {loc(f, 'type')}{fk && <> · <span style={{ color: CLSCOL[fk], fontWeight: 600 }}>{clsName(fk, lang)}</span></>}</>}
      title={<h2>{loc(f, 'title')}</h2>} amount={f.diff != null ? <div className="amt">{fmt(f.diff)}</div> : null} />
    <section>
      <table className="kv"><tbody>
        {f.expected != null && <><tr><td>{t('expected')}</td><td>{fmt(f.expected)}</td></tr><tr><td>{t('actual')}</td><td>{fmt(f.actual)}</td></tr></>}
        <tr><td>{t('pages')}</td><td><PageLinks pages={f.pages ?? []} /></td></tr>
      </tbody></table>
      {f.node && <ul className="fl"><li><button data-node={f.node} onClick={() => c.go(f.node!)}><span>{g.nameOf(f.node, lang)}</span><b>{fmt(g.amountOf(f.node))}</b></button></li></ul>}
    </section>
  </>;
}

export function KpiDetails({ k }: { k: Kpi }) {
  const { t, fmt, loc } = useText();
  return <>
    <Head kind={t('tab_' + k.tab)} title={<h2>{loc(k, 'label')}</h2>}
      amount={<div className="amt">{k.unit === 'count' ? nf0().format(k.value) : fmt(k.value)}</div>}>
      <div className="shares">{loc(k, 'sub')}{k.prev != null && <><br />{t('prevYear')}: {fmt(k.prev)} · <Change v={k.value} p={k.prev} /></>}</div>
    </Head>
    <section>
      <h3>{t('src')}</h3>
      <RefBlock rid={k.ref} col={k.col} />
      {k.prev_ref && k.prev_ref !== k.ref && <RefBlock rid={k.prev_ref} col={k.prev_col} label={t('prevYear')} />}
    </section>
  </>;
}
