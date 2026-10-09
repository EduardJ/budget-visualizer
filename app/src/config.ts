import type { DatasetConfig, RankingTab, SankeyTab, TabConfig } from './types';

let current: DatasetConfig | null = null;

export function setConfig(c: DatasetConfig) {
  current = c;
  for (const cat of c.categories) document.documentElement.style.setProperty('--c-' + cat.id, cat.color);
}

export function cfg(): DatasetConfig {
  if (!current) throw new Error('dataset config not loaded');
  return current;
}

export const tabs = (): TabConfig[] => cfg().tabs;
export const tabIds = () => tabs().map(t => t.id);
export const tabById = (id: string) => tabs().find(t => t.id === id);
export const firstTab = () => tabs()[0].id;
export const catIds = () => cfg().categories.map(c => c.id);
export const pdfHref = (page: number) => `${cfg().pdf}#page=${page}`;
export const colName = (k: string) => cfg().columns?.[k] ?? k;

export const sankeyTabs = () => tabs().filter((t): t is SankeyTab => t.layout === 'sankey');
export const checksTabId = () => tabs().find(t => t.layout === 'checks')?.id ?? firstTab();
export const rankingFor = (kind: string) => tabs().find((t): t is RankingTab => t.layout === 'ranking' && t.kind === kind);

/** The tab that shows a node's data chunk; core nodes belong on the first tab. */
export function tabForChunk(chunk: string) {
  if (chunk === 'core') return firstTab();
  return tabs().find(t => t.chunk === chunk)?.id ?? firstTab();
}

/** The section a chunk holds (for nodes whose own data is not loaded yet). */
export const sectionOfChunk = (chunk: string) => cfg().chunks?.[chunk]?.[0];

export function isIncome(id: string) {
  const inc = cfg().income;
  if (!inc) return false;
  return (inc.prefixes ?? []).some(p => id.startsWith(p)) || (inc.ids ?? []).includes(id);
}

export const isNegative = (id: string) => (cfg().negative ?? []).includes(id);
