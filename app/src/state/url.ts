import { ui } from './store';

// Inside sandboxed previews (e.g. an iframe with srcdoc, URL about:srcdoc) the History API throws.
// Probe once; if it fails keep navigation in an in-memory stack so in-app Back/Forward still work and nothing throws.
const HIST = { ok: true, stack: [] as string[], pos: -1 };
let memHash = '';

export function probeHistory() {
  try { history.replaceState(history.state, '', location.href); } catch { HIST.ok = false; }
  if (!HIST.ok) { HIST.stack = [memHash]; HIST.pos = 0; }
  publish();
}

export const currentHash = () => (HIST.ok ? location.hash : memHash);

export function writeHash(h: string, replace?: boolean) {
  if (HIST.ok) {
    try {
      if (replace) history.replaceState(null, '', h); else history.pushState(null, '', h);
      return;
    } catch { HIST.ok = false; }
  }
  memHash = h;
  if (replace && HIST.pos >= 0) HIST.stack[HIST.pos] = h;
  else { HIST.stack.length = HIST.pos + 1; HIST.stack.push(h); HIST.pos = HIST.stack.length - 1; }
  publish();
}

/** Step through the in-memory history; returns false at either end. */
export function memStep(d: number) {
  const p = HIST.pos + d;
  if (p < 0 || p >= HIST.stack.length) return false;
  HIST.pos = p;
  memHash = HIST.stack[p];
  publish();
  return true;
}

function publish() {
  ui().set({ hist: { memory: !HIST.ok, canBack: HIST.pos > 0, canFwd: HIST.pos < HIST.stack.length - 1 } });
}
