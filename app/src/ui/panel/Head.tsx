import type { ReactNode } from 'react';
import { useRuntime, useText } from '../common';

export function Head({ kind, title, amount, children }: { kind: ReactNode; title: ReactNode; amount?: ReactNode; children?: ReactNode }) {
  const { c } = useRuntime(), { t } = useText();
  return (
    <div className="ph">
      <button className="x" data-close aria-label={t('close')} onClick={() => { c.closePanel(); c.setHash(); }}>×</button>
      <div className="kind">{kind}</div>
      {title}
      {amount}
      {children}
    </div>
  );
}

export function CopyButton({ onClick }: { onClick: () => void }) {
  const { t } = useText();
  return <div style={{ marginTop: 8 }}><button className="copy" onClick={onClick}>{t('copy')}</button></div>;
}
