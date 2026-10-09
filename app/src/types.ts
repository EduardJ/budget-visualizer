// Shapes of data.json and dataset.json. schema/*.schema.json is the contract; keep the two in sync.

export type Dict<T> = Record<string, T>;

export interface Ref {
  page: number;
  pages?: number[];
  table: string;
  row?: string;
  original_label: string;
  quote: string;
  unit: string;
  values: Dict<string>;
  method?: 'parsed' | 'computed' | 'ocr' | 'manual';
  top?: number | null;
  components?: string[];
  note?: string;
}

export interface FundingSource {
  amount: number;
  ref: string;
  cats?: Dict<number>;
  [localized: string]: unknown;
}

export interface BudgetNode {
  id: string;
  kind: string;
  section?: string;
  level?: number;
  parent?: string | null;
  owner?: string;
  anchor?: string;
  amount: number;
  ref?: string | null;
  refCol?: string | null;
  cats?: Dict<number>;
  staff?: number;
  sources?: Dict<FundingSource>;
  prev?: number;
  prev_ref?: string;
  prevCol?: string;
  multi?: Dict<number>;
  head_ref?: string;
  src_refs?: string[];
  revenue?: { label: string; amount: number; prev?: number; ref: string }[];
  flags?: string[];
  en_src?: string;
  macro?: boolean;
  stock?: boolean;
  code?: string;
  table?: string;
  dates?: string;
  fund?: string[];
  prop_code?: string;
  sub_label?: string;
  [extra: string]: unknown;
}

export interface Flow {
  id: string;
  source: string;
  target: string;
  amount: number;
  ref: string | null;
  col?: string;
  kind: 'hard' | 'category' | 'project' | 'difference' | 'source-link';
  [extra: string]: unknown;
}

export interface Check {
  id: string;
  title: string;
  expected: number | null;
  actual: number | null;
  diff: number | null;
  status: 'pass' | 'fail';
  cls?: 'error' | 'rounding' | null;
  kind: string;
  unit?: string | null;
  group?: string;
  pages: number[];
  refs?: string[];
  [extra: string]: unknown;
}

export interface Finding {
  type: 'mismatch' | 'ambiguity' | 'note' | 'naming';
  title: string;
  cls?: 'error' | 'rounding' | null;
  expected?: number;
  actual?: number;
  diff?: number;
  unit?: string;
  pages?: number[];
  node?: string;
  [extra: string]: unknown;
}

export interface Kpi {
  tab: string;
  key: string;
  value: number;
  unit?: 'eur' | 'count';
  ref?: string | null;
  col?: string | null;
  prev?: number | null;
  prev_ref?: string | null;
  prev_col?: string | null;
  node?: string | null;
  [localized: string]: unknown;
}

export interface TourStep { node: string; flow?: string | null; [localized: string]: unknown }
export interface Tour { id: string; steps: TourStep[]; [localized: string]: unknown }

/** [id, name in the document language, English name, amount, kind, table, pages, chunk, code] */
export type SearchRow = [string, string, string, number, string, string, (number | null)[], string, string];

export interface Chunk { nodes: BudgetNode[]; flows: Flow[]; refs: Dict<Ref> }

export interface Meta { law: string; gazette?: string; pdf: string; pages?: number; [extra: string]: unknown }

export interface CoreData extends Chunk {
  meta: Meta;
  sources: unknown[];
  kpis: Kpi[];
  checks: Check[];
  findings: Finding[];
  tours: Tour[];
  summary: Dict<unknown>;
  need: Dict<string[]>;
  flowChunk: Dict<string>;
  search: SearchRow[];
}

export interface BudgetData extends Chunk {
  meta: Meta;
  sources: unknown[];
  kpis: Kpi[];
  checks: Check[];
  findings: Finding[];
  tours: Tour[];
  summary: Dict<unknown>;
}

export type Localized = Dict<string>;

export interface SankeyColumn {
  x: number;
  header: string;
  labelSide?: 'left' | 'right';
  labelWidth?: number;
  headerWidth?: number;
  nodes: string[];
}

export interface SortOption { id: string; label: string; share?: string }

interface TabBase { id: string; title: string; chunk?: string }
export interface SankeyTab extends TabBase { layout: 'sankey'; width?: number; height?: number; columns: SankeyColumn[] }
export interface CardsTab extends TabBase { layout: 'cards'; kind: string; columns?: number; note?: string; sort?: SortOption[] }
export interface RankingTab extends TabBase { layout: 'ranking'; kind: string; top?: number; perColumn?: number; category?: string }
export interface ChecksTab extends TabBase { layout: 'checks' }
export type TabConfig = SankeyTab | CardsTab | RankingTab | ChecksTab;

export type PaletteKey = 'rev' | 'fin' | 'gold' | 'flag' | 'ink3';

export interface DatasetConfig {
  id: string;
  pdf: string;
  sourceLang: string;
  langs: string[];
  currency?: string;
  numberLocale?: string;
  totals: { budget: string; inflows?: string };
  categories: { id: string; color: string; name: Localized }[];
  colorRules?: { prefix: string; color: PaletteKey; ribbon?: 'source' | 'either' }[];
  income?: { prefixes?: string[]; ids?: string[] };
  negative?: string[];
  levels?: { id: string; label: string; sections: string[]; nodes?: string[] }[];
  chunks?: Dict<string[]>;
  tabs: TabConfig[];
  panel?: {
    prevCol?: string;
    sourceRefCol?: string;
    revenueCol?: string;
    checkRefCol?: string;
    extraRefs?: { field: string; col?: string; label: Localized }[];
    multiYear?: string[];
  };
  columns?: Dict<string>;
  flags?: Dict<Localized>;
  filters?: { minAmounts?: number[] };
  strings: Dict<Dict<string | string[]>>;
  assumptions?: Dict<string[]>;
}

/** Where the split build put each data file (relative to index.html). */
export interface Manifest { core: string; chunks: Dict<string>; snips: Dict<string> }

export type ReconFilter = 'error' | 'rounding' | 'pass' | 'note';
