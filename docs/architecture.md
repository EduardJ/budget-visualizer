# Architecture

```
 budget PDF ──► adapter (Python)  ──► data.json ─┐
                parse_*  → raw/*.csv              │      tools/ (Vite plugin)          app/ (browser)
                normalize → nodes, flows,         ├──►  validate against schema/  ──►  canvas engine  ─┐
                  refs, checks, findings, tours   │     split into chunks               React UI       ├─► page
                snippets → snippets/*.jpg ────────┤     (or inline everything)          controller     ┘
 dataset.json (how to present it) ────────────────┘
```

Two halves meet at one contract: **`data.json`** says what the document says (every number with its source),
**`dataset.json`** says how to present it (tabs, Sankey columns, categories, colours, labels). Both are described by
JSON Schemas in `schema/` and checked on every build. The viewer contains nothing specific to one document.

## Pipeline (Python, per dataset)

Lives in `datasets/<id>/adapter/`, with shared helpers in `pipeline/`. It runs on a developer machine and in CI, never in
the browser, and its output is committed, so building the site needs only Node.

1. **Extraction** (`parse_*.py`): pdfplumber word positions. A number belongs to the column whose header anchor is
   nearest to the number's right edge; every page range and column anchor is in `adapter/layout.py`. Output: one CSV
   row per printed line in `raw/`, plus the full institution names of Annex 1 (`parse_annex_names.py`, read by
   character position because Table 3.1 cuts names off). Never extracted by eye.
2. **Normalisation** (`normalize.py` exec-chains `normalize_part2.py` → `part3` → `part4` → `sq_text.py`): builds
   nodes, flows and refs from the CSVs, then runs every check with exact decimal arithmetic (`pipeline/exact.py`) and
   adds Albanian text for every check and finding (`sq_text.py` stops the run if any is missing).
3. **Snippets** (`snippets.py`): a highlighted crop of the printed row for the key references, one JPEG per ref.
4. **Verification** (`spotcheck.py`, `make verify`): a second extractor (poppler's pdftotext) re-reads the top 20,
   20 random and every flagged value and confirms each against its row label.

Re-running the pipeline on the same PDF reproduces `raw/` and `data.json` byte for byte; CI checks that on every push.
Snippet JPEGs depend on the pdfium version, so they are regenerated only when wanted.

## Build (tools/, Vite)

`tools/vite-plugin-dataset.ts` loads `datasets/$DATASET`, validates it (`tools/dataset.ts`: schema plus cross-references:
every ref exists, every flow end exists, every text exists in every UI language...), and splits the data:

- **core**: everything needed at start (overview nodes and flows, checks, findings, tours, headline figures) plus a
  compact search index of every node, and a map of which chunk each node lives in;
- **one chunk per `dataset.json` "chunks" entry** (here central, municipal, capital), parsed the first time a node in it
  is needed.

Two outputs from the same code ([ADR-004](decisions/ADR-004-split-and-single-file-builds.md)):

| | `npm run build` → `dist/` | `npm run build:single` → `dist-single/` |
|---|---|---|
| data | `data/<chunk>.<hash>.json`, fetched on demand | inline `<script type="application/json">` blocks |
| snippets | `snippets/<rid>.<hash>.jpg` | inline data URIs |
| first load | ~370 KB gzipped | 15 MB |
| use | GitHub Pages and any static host | offline copy, sandboxed iframes (no fetch, no History API) |

Content-hashed file names mean a new dataset never mixes with files a browser cached from the previous one.

## Viewer (app/src)

```
main.tsx            boot: config → core data → store → React (rendered synchronously) → controller.boot()
config.ts           the dataset config and helpers derived from it
types.ts            data.json / dataset.json types (mirror of schema/)
data/source.ts      where data comes from: manifest + fetch, or inline JSON blocks
data/graph.ts       loaded nodes/flows/refs, indexed (children, in/out flows); loads chunks in request order
state/store.ts      UI state (language, tab, panel, tour, filters, menus...): one small external store
state/selection.ts  what is selected and lit, derived from the panel and the tour (never stored twice)
state/filters.ts    which nodes the filters dim
state/url.ts        URL hash; falls back to an in-memory history where the History API throws
controller.ts       every user action; the only writer of UI state; owns engine and worlds; keeps the URL in sync
cite.ts             citation text and copying
canvas/layout.ts    immutable world layouts per tab type: sankey, cards, ranking, checks (typed Box union)
canvas/worlds.ts    each tab's layout, built on first use, and which tab can show a node or a flow
canvas/render.ts    one frame: ribbons and boxes, counter-scaled text clipped to its box, dimming, colours
canvas/engine.ts    the canvas element, camera and fly-to, pointer input, hit testing, the draw loop
ui/*.tsx, ui/panel/ React: header and search, tabs and headline figures, details panel, reconciliation, overlays
i18n.ts, strings.json   built-in UI text (sq, en), dataset strings override; localised fields name_<lang>
testHooks.ts        window.__canvas, what the browser tests drive and measure
```

**The canvas is not React** ([ADR-002](decisions/ADR-002-canvas-engine-outside-react.md)). It draws thousands of boxes,
ribbons and labels at 60 fps while the camera moves; React renders the DOM around it (panel, dialogs, search, headline
strip). The engine never reads or writes the store: the controller gives it a `view()` of what to draw (derived in
`state/selection.ts`), marks it dirty on every state change, and receives clicks and zoom-level changes back.

**The panel is the selection.** The selected box, the selected ribbon and what a tour lights up are derived from the
panel and the tour, so every action changes one thing and nothing can fall out of step.

**Semantic zoom.** Each tab is laid out once in world units; the camera only scales and pans. `levelOf(k)`: below 0.55
totals only, below 1.3 organisations by category with programme rows, otherwise everything. Text is drawn at world size
× zoom, clamped, cut with an ellipsis to its box, and skipped when the box is smaller than the font; any overflow is
recorded (`textOverflow()` in the tests must be empty).

**URL state.** `#tab=…&node=…&flow=…&tour=…&step=…&lang=…&fmt=short`. Every selection pushes a history entry, so the
browser's back and forward walk through what you looked at. Inside sandboxed iframes (`about:srcdoc`) the History API
throws; the page detects that once and keeps an in-memory history with ← / → buttons in the header.

**State changes commit synchronously.** The controller wraps store updates in `flushSync`, because the camera code
measures the panel and the tour bar right after a selection, and tests read the DOM right after an action.
