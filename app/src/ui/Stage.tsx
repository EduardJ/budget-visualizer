import { catIds, cfg } from '../config';
import { catName, loc, strList } from '../i18n';
import { useUI } from '../state/store';
import { useRuntime, useText } from './common';
import { Recon } from './Recon';

export function Stage() {
  return (
    <div id="stage">
      <canvas id="cv" aria-label="Budget canvas" tabIndex={0} />
      <Level />
      <Zoom />
      <Filters />
      <TourMenu />
      <TourBar />
      <Recon />
    </div>
  );
}

function Level() {
  const { t, lang } = useText();
  const lv = useUI(s => s.level), loading = useUI(s => s.loading);
  if (loading) return <div id="lvl">{t('loading')}</div>;
  return <div id="lvl"><b>{`${lv + 1}/3`}</b>{` · ${strList(lang, 'level')[lv]}${lv < 2 ? ' · ' + t('zoomhint') : ''}`}</div>;
}

function Zoom() {
  const { c } = useRuntime(), E = c.engine;
  return (
    <div id="zoomctl">
      <button id="z-in" aria-label="Zoom in" onClick={() => E.zoomCenter(1.4)}>+</button>
      <button id="z-out" aria-label="Zoom out" onClick={() => E.zoomCenter(1 / 1.4)}>−</button>
      <button id="z-fit" aria-label="Fit to screen" style={{ fontSize: 13 }} onClick={() => E.fitAll()}>⤢</button>
    </div>
  );
}

function Filters() {
  const { c } = useRuntime(), { t, fmt, lang } = useText();
  const open = useUI(s => s.menu === 'filters'), F = useUI(s => s.filt);
  const levels = cfg().levels ?? [], mins = cfg().filters?.minAmounts ?? [0, 1e5, 1e6, 1e7, 5e7];
  return (
    <div id="filters" role="dialog" aria-label="Filters" className={open ? 'open' : undefined}>
      <fieldset><legend>{t('cats')}</legend>
        {catIds().map(k => (
          <label key={k}><input type="checkbox" data-cat={k} checked={F.cats.has(k)} onChange={e => c.toggleCat(k, e.target.checked)} /><span className="sw" style={{ background: `var(--c-${k})` }} />{catName(k, lang)}</label>
        ))}
      </fieldset>
      {levels.length > 0 && <fieldset><legend>{levels.map(l => t(l.label)).join(' / ')}</legend>
        {levels.map(l => (
          <label key={l.id}><input type="checkbox" data-lvl={l.id} checked={F.levels[l.id] !== false} onChange={e => c.toggleLevel(l.id, e.target.checked)} />{t(l.label)}</label>
        ))}
      </fieldset>}
      <fieldset><legend>{t('minsize')}</legend>
        <select data-min value={F.min} onChange={e => c.setMin(+e.target.value)}>
          {mins.map(v => <option key={v} value={v}>{v ? fmt(v, 'short') : t('all')}</option>)}
        </select>
      </fieldset>
    </div>
  );
}

function TourMenu() {
  const { g, c } = useRuntime(), { t, lang } = useText();
  const open = useUI(s => s.menu === 'tours');
  return (
    <div id="tourmenu" role="menu" className={open ? 'open' : undefined}>
      {g.D.tours.map(tr => (
        <button key={tr.id} data-tour={tr.id} onClick={() => { c.closeMenus(); c.startTour(tr.id, 0); }}>
          {loc(tr, 'title', lang)}<small>{tr.steps.length} {t('steps')}</small>
        </button>
      ))}
    </div>
  );
}

function TourBar() {
  const { c } = useRuntime(), { t, lang } = useText();
  const tour = useUI(s => s.tour), step = useUI(s => s.step);
  if (!tour) return <div id="tourbar" role="region" aria-live="polite" />;
  const st = tour.steps[step], n = tour.steps.length;
  return (
    <div id="tourbar" role="region" aria-live="polite" className="on">
      <div className="t"><b>{loc(tour, 'title', lang)}</b><span>{`${t('step')} ${step + 1}/${n}`}</span></div>
      <p>{loc(st, 'text', lang)}</p>
      <div className="prog"><i style={{ width: `${(100 * (step + 1)) / n}%` }} /></div>
      <div className="btns">
        <button data-t="prev" disabled={step === 0} onClick={() => c.tourGo(step - 1)}>{t('prev')}</button>
        <button data-t="next" disabled={step === n - 1} onClick={() => c.tourGo(step + 1)}>{t('next')}</button>
        <button className="exit" data-t="exit" onClick={() => c.exitTour()}>{t('exit')}</button>
      </div>
    </div>
  );
}
