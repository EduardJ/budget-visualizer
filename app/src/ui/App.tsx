import { useRef } from 'react';
import { useUI } from '../state/store';
import { Header } from './Header';
import { Panel } from './panel/Panel';
import { Stage } from './Stage';
import { Kpis, Tabs } from './Tabs';

export function App() {
  return <>
    <div id="app">
      <Header />
      <div id="sub"><Tabs /><Kpis /></div>
      <Stage />
      <Panel />
    </div>
    <Toast />
  </>;
}

function Toast() {
  const toast = useUI(s => s.toast);
  const last = useRef('');
  if (toast) last.current = toast.msg; // keep the text while it fades out
  return <div id="toast" role="status" className={toast ? 'on' : undefined}>{last.current}</div>;
}
