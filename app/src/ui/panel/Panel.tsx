import { useLayoutEffect, useRef } from 'react';
import { useUI, type PanelView } from '../../state/store';
import { CheckDetails, FindingDetails, FlowDetails, KpiDetails } from './details';
import { NodeDetails } from './NodeDetails';

/** The details panel: whatever is selected, with the source of every number. */
export function Panel() {
  const view = useUI(s => s.panel), seq = useUI(s => s.panelSeq);
  const ref = useRef<HTMLElement>(null);
  useLayoutEffect(() => { if (ref.current) ref.current.scrollTop = 0; }, [seq]);
  return (
    <aside id="panel" ref={ref} aria-live="polite" className={view ? 'open' : undefined}>
      {view && <Body view={view} />}
    </aside>
  );
}

function Body({ view }: { view: PanelView }) {
  switch (view.type) {
    case 'node': return <NodeDetails id={view.id} />;
    case 'flow': return <FlowDetails id={view.id} />;
    case 'check': return <CheckDetails c={view.check} />;
    case 'finding': return <FindingDetails f={view.finding} />;
    case 'kpi': return <KpiDetails k={view.kpi} />;
  }
}
