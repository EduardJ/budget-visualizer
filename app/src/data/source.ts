import type { Chunk, CoreData, DatasetConfig, Dict, Manifest } from '../types';

// Two ways the data reaches the page:
//  - split build (GitHub Pages): index.html carries a manifest; core and each chunk are JSON files fetched on demand;
//  - single-file build: every chunk is an inert <script type="application/json"> block inside index.html,
//    parsed the first time it is needed. Used offline and in sandboxed iframes, where fetch has no base URL.
export interface DataSource {
  core(): Promise<CoreData>;
  chunk(name: string): Promise<Chunk>;
  snippet(refId: string): string | null;
}

const json = <T>(id: string): T | null => {
  const el = document.getElementById(id);
  if (!el) return null;
  const v = JSON.parse(el.textContent || 'null') as T;
  el.textContent = '';
  return v;
};

export function readConfig(): DatasetConfig {
  const c = json<DatasetConfig>('d-config');
  if (!c) throw new Error('index.html has no dataset config (#d-config)');
  return c;
}

export function createSource(): DataSource {
  const manifest = json<Manifest>('d-manifest');
  return manifest ? fetched(manifest) : inline();
}

function inline(): DataSource {
  let snips: Dict<string> | null = null;
  return {
    core: async () => {
      const c = json<CoreData>('d-core');
      if (!c) throw new Error('index.html has neither a data manifest nor inline core data');
      return c;
    },
    chunk: async name => {
      const c = json<Chunk>('d-' + name);
      if (!c) throw new Error('no inline data chunk ' + name);
      return c;
    },
    snippet: rid => (snips ??= json<Dict<string>>('d-snips') ?? {})[rid] ?? null,
  };
}

function fetched(m: Manifest): DataSource {
  const get = async <T>(url: string): Promise<T> => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return r.json() as Promise<T>;
  };
  return {
    core: () => get<CoreData>(m.core),
    chunk: name => {
      const url = m.chunks[name];
      if (!url) return Promise.reject(new Error('unknown data chunk ' + name));
      return get<Chunk>(url);
    },
    snippet: rid => m.snips[rid] ?? null,
  };
}
