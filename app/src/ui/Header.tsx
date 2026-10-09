import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { cfg } from '../config';
import { fmt } from '../format';
import { kindName } from '../i18n';
import { createSearch, type SearchHit } from '../search';
import { useUI } from '../state/store';
import { useRuntime, useText } from './common';

export function Header() {
  const { c } = useRuntime(), { t, lang, mode } = useText();
  const menu = useUI(s => s.menu);
  return (
    <header>
      <div className="brand"><b id="t-title">{t('title')}</b><span id="t-sub">{t('sub')}</span></div>
      <Search />
      <div className="grow" />
      <div className="seg" role="group" aria-label="Language">
        {cfg().langs.map(l => <button key={l} id={'l-' + l} aria-pressed={lang === l} onClick={() => c.setLang(l)}>{l.toUpperCase()}</button>)}
      </div>
      <div className="seg" role="group" aria-label="Amount format">
        <button id="f-full" aria-pressed={mode === 'full'} onClick={() => c.setFmt('full')}>{fmt(1234567, 'full')}</button>
        <button id="f-short" aria-pressed={mode === 'short'} onClick={() => c.setFmt('short')}>{fmt(1234567, 'short')}</button>
      </div>
      <button className="tb" id="b-filter" aria-expanded={menu === 'filters'} onClick={() => c.toggleMenu('filters')}>{t('filters')}</button>
      <button className="tb" id="b-tours" aria-expanded={menu === 'tours'} onClick={() => c.toggleMenu('tours')}>{t('tours')}</button>
      <button className="tb" id="b-recon" onClick={() => c.openRecon()}>{t('recon')}</button>
      <HistoryNav />
    </header>
  );
}

function Search() {
  const { g, c } = useRuntime(), { t, nm, fmt, lang } = useText();
  const search = useMemo(() => createSearch(g.D.search), [g]);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState(-1);
  const results = useMemo(() => search(q), [search, q]);
  const box = useRef<HTMLDivElement>(null), input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const away = (e: MouseEvent) => { if (!(e.target as HTMLElement).closest('#search')) setOpen(false); };
    document.addEventListener('click', away);
    return () => document.removeEventListener('click', away);
  }, []);
  useEffect(() => { box.current?.querySelector('.on')?.scrollIntoView({ block: 'nearest' }); }, [sel]);

  const pick = (n: SearchHit) => { setOpen(false); input.current?.blur(); c.go(n.id); };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      setSel(s => Math.max(0, Math.min(results.length - 1, s + (e.key === 'ArrowDown' ? 1 : -1))));
    }
    if (e.key === 'Enter' && results[sel]) pick(results[sel]);
  };
  return (
    <div id="search">
      <input id="q" ref={input} type="search" autoComplete="off" aria-label={t('search')} placeholder={t('search')} value={q}
        onChange={e => { const v = e.target.value; setQ(v); setSel(search(v).length ? 0 : -1); setOpen(!!v.trim()); }} onKeyDown={onKey} />
      <div id="results" role="listbox" ref={box} style={{ display: open && q.trim() ? 'block' : 'none' }}>
        {results.length ? results.map((n, i) => (
          <button key={n.id} role="option" aria-selected={i === sel} data-i={i} className={i === sel ? 'on' : ''} onClick={() => pick(n)}>
            <span>{nm(n)}</span><b>{fmt(n.amount)}</b>
            <small>{kindName(n.kind, lang)} · {n.table} · {t('page')} {n.pages.join(',')} · {t('tab_' + c.worlds.naturalTab(n.id))}</small>
          </button>
        )) : <button disabled><span>{t('noResults')}</span></button>}
      </div>
    </div>
  );
}

function HistoryNav() {
  const { c } = useRuntime();
  const h = useUI(s => s.hist);
  return (
    <span className="seg" id="nav-mem" style={{ display: h.memory ? 'inline-flex' : 'none' }} role="group" aria-label="History">
      <button data-nav="back" aria-label="Back" disabled={!h.canBack} onClick={() => c.memNav(-1)}>←</button>
      <button data-nav="fwd" aria-label="Forward" disabled={!h.canFwd} onClick={() => c.memNav(1)}>→</button>
    </span>
  );
}
