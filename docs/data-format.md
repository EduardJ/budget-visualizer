# Data format

Every dataset folder holds:

```
datasets/<id>/
  dataset.json     how to present it (schema/dataset.schema.json), written by hand
  data.json        what the document says (schema/data.schema.json), produced by the adapter, never edited by hand
  <document>.pdf   the source; published next to index.html, every reference links to <pdf>#page=N
  snippets/        optional: r<n>.jpg, a crop of the printed row behind reference r<n>
  raw/, adapter/   the extraction (Python); not read by the viewer
```

`npm run validate` checks both files against their schemas and then everything a schema cannot express. The build runs
the same validation and refuses to publish a dataset that fails it.

## Localised text

Text in more than one language uses one field per language: `name_sq`, `name_en`, `title_sq`, `note_en`... The viewer
looks for `<field>_<lang>`, then `<field>_en`, then the unsuffixed `<field>`, then `<field>_<sourceLang>`. For checks
and findings the unsuffixed `title`, `note` and `type` are English (historical). Every node must have
`name_<sourceLang>`, its name as printed. Every check, finding, tour, step and headline figure must have its text in
every UI language listed in `dataset.json` (the build fails otherwise).

## data.json

All amounts are in euros (or the document's currency), never millions, whatever unit the table was printed in. The
unit is kept on each reference.

### refs: where a number was printed

`refs["r123"]`:

| field | |
|---|---|
| `page`, `pages?` | PDF page(s), 1-based |
| `table` | table name as printed (`"Tabela 3.1"`), or `"computed"` |
| `row`, `original_label` | the row label, as printed |
| `quote` | the whole printed line, raw |
| `unit` | `"EUR"`, `"EUR million"`... |
| `values` | column → printed token, exactly as printed: `{"total": "1,194,770,851", "y2027": "1,207,550,000"}` |
| `method` | `parsed` (default) or `computed`; `ocr` and `manual` are shown with a "needs review" badge |
| `top` | y of the line on the page in points; used to crop the snippet |
| `components` | for computed refs: the node ids that were summed |

Ref ids are renumbered every time `normalize.py` runs, so `snippets/` must be regenerated with it.

### nodes

| field | |
|---|---|
| `id` | stable id, e.g. `rev:vatbor`, `org:208`, `org:208/p0/s20801`, `mun:616`, `proj:3.2:12345:7` |
| `kind` | `line group pool dest category org programme subprogramme municipality project difference` |
| `section` | part of the document; decides the data chunk and the government-level filter |
| `parent` | hierarchy parent; children become card rows |
| `owner` | for projects: the organisation running it |
| `anchor` | a node to show on screen in its place (stocks, GDP) |
| `amount`, `ref`, `refCol` | the figure, the ref it comes from, and which column of `ref.values` holds it |
| `cats` | amount per economic category id |
| `staff`, `sources` | staff count; amount per funding source with its own ref |
| `prev`, `prev_ref`, `prevCol` | the previous year's figure and source |
| `multi` | multi-year amounts of a project |
| `head_ref`, `src_refs` | a project's own line and its funding-source lines |
| `revenue` | a municipality's revenue lines (Table 4.3 in the Kosovo law) |
| `flags` | `RECONCILIATION` (children do not sum to the parent), `ROUNDING`, `AMBIGUITY`, `NAME_TRUNCATED_IN_TABLE`, or dataset-specific ones labelled in `dataset.json` "flags" |
| `en_src` | `translated`, `sq-only` or `proper noun`: where the English name comes from |
| `macro`, `stock` | an indicator or an end-of-year stock, not a flow of the year |

A `difference` node is created whenever children do not add up to their parent, whatever the size of the gap.

### flows

`{id, source, target, amount, ref, col, kind}`, kind: `hard` (stated in the document), `category` (an organisation's
spending in one economic category), `project`, `difference`, `source-link` (linked by funding-source label, not stated).

### checks

`{id, title, title_<lang>, expected, actual, diff, status: pass|fail, cls: error|rounding|null, bound, kind, unit, group,
pages, refs, note, note_<lang>}`. `bound` is the largest gap rounding of the printed digits could explain; it decides
`cls`. See [checks.md](checks.md).

### findings

The individual rows behind failing checks, plus ambiguities and notes:
`{type: mismatch|ambiguity|note|naming, title, title_<lang>, type_<lang>, expected?, actual?, diff?, cls?, pages, node?}`.

### kpis and tours

`kpis[]`: headline figures per tab `{tab, key, label_<lang>, sub_<lang>, value, unit: eur|count, ref, col, prev, prev_ref, prev_col, node}`.
Clicking one opens its node, or its own source when it has no node. The checks tab computes its headline figures from
the checks.

`tours[]`: guided tours along the money trail `{id, title_<lang>, steps: [{node, flow?, text_<lang>}]}`.

## dataset.json

| key | |
|---|---|
| `id`, `pdf` | folder name; the source PDF in the folder |
| `sourceLang`, `langs` | the document's language; UI languages, first is the default |
| `currency`, `numberLocale` | `"€"`, `"en-US"` (digit grouping) |
| `totals` | `budget`: node for "share of the total budget"; `inflows`: node for "share of all inflows" and the Sankey scale |
| `categories` | `[{id, color, name: {<lang>: …}}]` in display order; category nodes are `cat:<id>` |
| `colorRules` | node and ribbon colour by id prefix: `[{prefix: "fin:", color: "fin", ribbon: "either"}]` |
| `income` | ids or prefixes shown as "share of all inflows" |
| `negative` | nodes stored positive but shown with a minus (refunds) |
| `levels` | the government-level filter: `[{id, label, sections, nodes}]` |
| `chunks` | lazy data chunks: name → node sections in it; everything else, and every node on a Sankey tab, is core |
| `tabs` | the views, see below |
| `panel` | which ref columns the details panel shows: `prevCol`, `sourceRefCol`, `revenueCol`, `checkRefCol`, `extraRefs`, `multiYear` |
| `columns` | display names of ref value columns |
| `flags` | labels for dataset-specific flags |
| `filters.minAmounts` | thresholds of the "dim items under" filter |
| `strings` | per language: `title`, `sub`, `documentTitle`, every tab title key and `tab_<id>`, Sankey headers, notes; may override any built-in string in `app/src/strings.json` |
| `assumptions` | per language: the assumptions listed in the reconciliation dialog |

### tabs

```jsonc
{ "id": "flow", "layout": "sankey", "title": "s1", "width": 3200, "height": 1500,
  "columns": [ { "x": 380, "header": "in", "labelSide": "left", "nodes": ["rev:vatbor", "..."] }, "..." ] }
{ "id": "central", "layout": "cards", "title": "s2", "chunk": "central", "kind": "org", "columns": 8 }
{ "id": "municipal", "layout": "cards", ..., "note": "noPop", "sort": [{ "id": "wages", "label": "byWages", "share": "wages" }] }
{ "id": "capital", "layout": "ranking", "title": "s4", "chunk": "capital", "kind": "project", "top": 150, "perColumn": 50, "category": "capital" }
{ "id": "findings", "layout": "checks", "title": "s5" }
```

- `sankey`: columns of node ids stacked top to bottom, heights proportional to amount (`height` world units = the
  inflows total); ribbons are the core flows whose both ends are in the columns.
- `cards`: one card per node of `kind`, its descendants as rows, an economic-category bar; optional sort options.
- `ranking`: the `top` largest nodes of `kind`, `perColumn` per column, the rest summarised.
- `checks`: every check and finding, errors first.

`title` and `header` are string keys, looked up in `strings`.
