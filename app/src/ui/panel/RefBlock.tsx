import type { ReactNode } from 'react';
import { colName, pdfHref } from '../../config';
import { NodeLink, useRuntime, useText } from '../common';

/** The source of a number: table, page, printed row and value, a crop of the page, and a link into the PDF. */
export function RefBlock({ rid, col, label }: { rid: string | null | undefined; col?: string | null; label?: string }) {
  const { g, source } = useRuntime(), { t, nm } = useText();
  const r = rid ? g.REFS[rid] : undefined;
  if (!rid || !r) return <div className="ref"><span className="badge b-rec">{t('noRef')}</span></div>;
  const pages = r.pages || [r.page];
  const ov = col && r.values && r.values[col];
  const meth = r.method || 'parsed';
  const snipSrc = source.snippet(rid);
  let snip: ReactNode = null;
  if (snipSrc) snip = <div className="snip"><img alt={`Snippet of ${r.table} page ${r.page}`} src={snipSrc} /></div>;
  else if (meth !== 'computed' && r.values && Object.keys(r.values).length) {
    const ks = Object.keys(r.values);
    snip = (
      <div className="rt"><table><tbody>
        <tr><th style={{ textAlign: 'left' }}>{r.table}</th>{ks.map(k => <th key={k}>{colName(k)}</th>)}</tr>
        <tr className="hl"><td style={{ textAlign: 'left' }}>{(r.original_label || '').slice(0, 60)}</td>{ks.map(k => <td key={k}>{r.values[k]}</td>)}</tr>
      </tbody></table></div>
    );
  }
  return (
    <div className="ref">
      {label && <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>}
      <div className="meta">
        <span>{r.table === 'computed' ? t('computed') : r.table}</span>
        <span>{t('page')} {pages.join(', ')}</span>
        <span>{t('unit')}: {r.unit}</span>
        <span className={'badge b-' + meth}>{meth === 'computed' ? t('computed') : meth}</span>
        {(meth === 'ocr' || meth === 'manual') && <span className="badge b-amb">{t('reviewFlag')}</span>}
      </div>
      <div className="meta">
        <span>{t('row')}: {r.row || r.original_label}</span>
        {ov && <span>{t('orig')}: <b>{ov}</b>{col && col !== 'total' ? ' (' + colName(col) + ')' : ''}</span>}
      </div>
      <blockquote>{r.quote}</blockquote>
      {r.components && (
        <div className="note">= {r.components.map((c, i) => <span key={c}>{i ? ' + ' : ''}{g.N.get(c) ? <NodeLink id={c}>{nm(g.N.get(c))}</NodeLink> : c}</span>)}</div>
      )}
      {snip}
      <div className="acts">{pages.slice(0, 3).map(p => <a key={p} href={pdfHref(p)} target="_blank" rel="noopener">{t('open')} · p.{p}</a>)}</div>
    </div>
  );
}
