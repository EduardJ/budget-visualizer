import { useMemo } from 'react';
import { cfg } from '../config';
import { ckv, clsName, clsOf, CLSCOL, findingCls, findingDiff } from '../checks';
import { useUI } from '../state/store';
import type { ReconFilter } from '../types';
import { NodeLink, PageLinks, useRuntime, useText } from './common';

const RANK = { error: 0, rounding: 1, pass: 2 } as const;

/** Every check and finding, filterable by class, with the assumptions behind them. */
export function Recon() {
  const open = useUI(s => s.recon);
  return <div id="recon" role="dialog" aria-label="Reconciliation" className={open ? 'open' : undefined}>{open && <ReconBody />}</div>;
}

function ReconBody() {
  const { g, c } = useRuntime(), { t, lang, mode, loc } = useText();
  const flt = useUI(s => s.clsFilter) ?? 'all';
  const { checks: allChecks, findings } = g.D;
  const cnt = (k: string) => allChecks.filter(x => clsOf(x) === k).length;
  const fcnt = (k: string) => findings.filter(f => f.type === 'mismatch' && (f.cls || 'error') === k).length;
  const noRef = Number(allChecks.find(x => x.id === 'refs')?.actual) || 0;
  const checks = useMemo(() => allChecks.filter(x => flt === 'all' || clsOf(x) === flt)
    .sort((a, b) => RANK[clsOf(a)] - RANK[clsOf(b)] || String(a.group || '').localeCompare(String(b.group || ''))), [allChecks, flt]);
  const finds = useMemo(() => findings.map((f, i) => [f, i] as const)
    .filter(([f]) => flt === 'all' || (f.type === 'mismatch' ? f.cls || 'error' : 'note') === flt || (flt === 'note' && f.type !== 'mismatch')), [findings, flt]);
  const notes = findings.filter(f => f.type !== 'mismatch').length;
  const btn = (k: ReconFilter | 'all', label: string, n?: number) => (
    <button className="tb" data-flt={k} aria-pressed={flt === k} style={flt === k ? { background: 'var(--ink)', color: '#fff' } : undefined}
      onClick={() => c.setClsFilter(k === 'all' ? null : k)}>{label}{n != null ? ' · ' + n : ''}</button>
  );
  return <>
    <div className="rh">
      <h2>{t('recon')}</h2>
      {btn('all', t('allFilter'))}{btn('error', clsName('error', lang), cnt('error') + fcnt('error'))}{btn('rounding', clsName('rounding', lang), cnt('rounding') + fcnt('rounding'))}
      {btn('pass', clsName('pass', lang), cnt('pass'))}{btn('note', t('notesFilter'), notes)}
      <span>{noRef} {t('noSource')}</span>
      <button className="tb x" data-x onClick={() => c.closeRecon()}>{t('close')}</button>
    </div>
    <div className="wrap">
      <p className="note" style={{ margin: 10 }}>{t('noTolerance')}</p>
      {flt !== 'note' && <>
        <h3>{t('checks')} ({checks.length})</h3>
        <table><tbody>
          <tr><th>{t('cls')}</th><th>{t('check')}</th><th>{t('group')}</th><th className="n">{t('expected')}</th><th className="n">{t('actual')}</th><th className="n">{t('diff')}</th><th>{t('pages')}</th></tr>
          {checks.map(x => {
            const k = clsOf(x), note = loc(x, 'note');
            return (
              <tr key={x.id}>
                <td style={{ color: CLSCOL[k], fontWeight: 600, whiteSpace: 'nowrap' }}>{clsName(k, lang)}</td>
                <td>{loc(x, 'title')}{note && <><br /><small style={{ color: 'var(--ink-2)' }}>{note}</small></>}</td>
                <td>{x.group || ''}</td>
                <td className="n">{ckv(x, x.expected, mode)}</td><td className="n">{ckv(x, x.actual, mode)}</td><td className="n">{k === 'pass' ? '0' : ckv(x, x.diff, mode)}</td>
                <td><PageLinks pages={x.pages} max={6} /></td>
              </tr>
            );
          })}
        </tbody></table>
      </>}
      {flt !== 'pass' && <>
        <h3>{t('findings')} ({finds.length})</h3>
        <table><tbody>{finds.map(([f, i]) => {
          const fk = findingCls(f);
          return (
            <tr key={i}>
              <td style={{ whiteSpace: 'nowrap', color: fk ? CLSCOL[fk] : 'var(--ink-2)', fontWeight: 600 }}>{fk ? clsName(fk, lang) : loc(f, 'type')}</td>
              <td>{loc(f, 'title')}{f.node && <> · <NodeLink id={f.node} onNavigate={() => c.closeRecon()}>→</NodeLink></>}</td>
              <td className="n">{f.diff != null ? findingDiff(f, mode) : ''}</td>
              <td><PageLinks pages={f.pages ?? []} /></td>
            </tr>
          );
        })}</tbody></table>
      </>}
      <h3>{t('assumptions')}</h3>
      <ul style={{ margin: '0 10px 0 28px', fontSize: 13, lineHeight: 1.5 }}>{(cfg().assumptions?.[lang] ?? []).map((a, i) => <li key={i}>{a}</li>)}</ul>
    </div>
  </>;
}
