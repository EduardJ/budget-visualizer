# Handover: Budget Visualizer

This file is for Claude Code. Read it fully before changing anything; the details live in `docs/`.

## What this is

A static budget visualizer: it lets anyone trace every euro of a budget law from where it comes from to where it is spent.
Every number on screen links back to the page, table and row it came from. It also audits the document: every printed
relation is re-computed exactly and every mismatch is shown.

The first dataset is Kosovo's 2026 budget law (Ligji Nr. 10/L-001, Gazeta Zyrtare Nr. 4, 2 mars 2026, 728 pages) in
`datasets/kosovo-2026/`. The viewer is generic; another edition or another document is a new dataset folder
(`docs/new-dataset.md`).

The owner is Eduard (product/tech, Prishtinë; works in Albanian and English). He is direct and wants things
done properly rather than explained. Albanian (SQ) is the default UI language.

## Non-negotiable rules (from the owner)

1. **The PDF is the only source of numbers.** No outside figures, no estimates. If the PDF is wrong, show it as a finding; never "fix" it.
2. **Every number needs a source reference** (`ref`: page, table, row, original label, original printed value, unit, method). The check `refs` must stay at 0 nodes/flows without a reference.
3. **No tolerance in checks.** A check passes only when the printed figures agree exactly. Failures are labelled
   - `error` (arithmetic error): the gap is larger than rounding of the printed digits could produce, or two prints of the *same* figure differ at all;
   - `rounding` (rounding only): the gap is within the rounding of the printed digits (half a unit of the last printed digit per figure summed).
   Both are shown. Do not hide, merge or soften failures.
4. **Albanian and English for everything user-facing**, including every check and finding title and note. `adapter/sq_text.py` stops the pipeline and `tools/dataset.ts` stops the build if any is missing — keep it that way.
5. **Layout is identical at every zoom level.** Zoom only changes what is drawn. Filters dim, never move. Counter-scaled text must never overflow its box (tests measure this).
6. **Show your verification.** After changes, run the tests and the PDF spot-check and report the actual numbers.

## Repository layout

```
app/                         viewer: Vite + TypeScript + React
  src/canvas/                  not React: layout.ts (immutable world per tab type), worlds.ts (layouts per tab, which tab
                               shows a node), render.ts (drawing, text fitting, dimming), engine.ts (canvas, camera, input, hit test)
  src/controller.ts            every user action; only writer of UI state; owns engine + worlds; URL sync; keyboard
  src/state/                   store.ts (UI state), selection.ts (selection/highlight derived from panel + tour),
                               filters.ts (dimming policy), url.ts (hash + in-memory history fallback)
  src/data/                    source.ts (manifest+fetch or inline JSON), graph.ts (indexes, chunk loading)
  src/ui/                      React components (header/search, tabs/KPIs, panel, reconciliation, overlays)
  src/i18n.ts, strings.json    built-in UI text sq/en; dataset strings override; loc() for <field>_<lang>
  src/testHooks.ts             window.__canvas for the tests
datasets/kosovo-2026/        budget-2026.pdf, dataset.json (presentation), data.json (pipeline output),
                             raw/*.csv, snippets/r<n>.jpg, adapter/ (the Kosovo extraction code, layout.py)
pipeline/                    shared Python: paths, pdfutil, exact (decimal checks), snippets, spotcheck, inspect_page
schema/                      dataset.schema.json, data.schema.json (the contract; keep app/src/types.ts in sync)
tools/                       dataset.ts (load, validate, chunk), vite-plugin-dataset.ts, validate.ts
tests/                       Playwright specs + fixtures/minimal (synthetic second dataset)
docs/                        architecture, data-format, new-dataset, checks, development, deploying, decisions/ (ADRs)
.github/workflows/pages.yml  PRs: test; main: test, re-extract and compare, deploy to GitHub Pages
```

## Commands

```bash
npm ci && npm run dev              # viewer with live reload (Vite prints the port)
npm run check                      # typecheck + validate dataset + build dist/, dist-single/, dist-fixture/ + all browser tests
npm run validate                   # dataset only
make extract data snippets         # PDF -> raw/ -> data.json -> snippets/ (needs .venv: pip install -r requirements.txt)
make verify                        # pdftotext re-read (needs poppler)
make help                          # everything; DATASET=<folder> picks the dataset
```

## Verification (run after every change, report actual numbers, look at tests/shots/)

Expected today:
- `layout.spec` on pages, single-file and fixture: every tab `[true, 0, true, 0]` (identical, overlaps, fit, overflow)
- `generic.spec`: 40/40 (kosovo-2026, both builds), 23/23 (fixture)
- `interact.spec`: 64/64 on both builds (the 59 original checks + DPR 2 ribbons, projects tab owners)
- `sandbox.spec`: 8/8
- `make verify`: top20 20/20, random20 13/13, flagged 15/15
- pipeline determinism: `make extract data` leaves `git diff datasets/*/raw datasets/*/data.json` empty

## Pipeline (datasets/<id>/adapter, see docs/architecture.md)

1. Extraction (`parse_*.py`): pdfplumber word positions; columns by the x of a number's right edge against anchors in
   `layout.py`. Never extract by eye. Known PDF quirks handled: glyph-split numbers in Annex 1 (`lines_merged`), labels
   that wrap to the next line, truncated institution names (full names from Annex 1), a value printed across three
   lines on p.32, malformed project dates (separated by character x-position, `band_text`), invisible spaces printed
   over bold glyphs in Annex 1 names (`parse_annex_names.py`).
2. Normalisation (`normalize.py` exec's `normalize_part2.py` → `part3` → `part4` → `sq_text.py`): refs, nodes, flows,
   checks (exact arithmetic, `pipeline/exact.py`), findings, tours, KPIs, Albanian text. `glossary.py`: English labels.
3. Snippets (`snippets.py` → `pipeline/snippets.py`), verification (`spotcheck.py` → `pipeline/spotcheck.py`).

When you add a check: `title_sq`/`note_sq`, a `group`, the `pages`, `refs` to the rows involved, the correct rounding
bound (use `X`/`RT`/`CL` in part 4). Details: `docs/checks.md`.

## Data model

`docs/data-format.md` field by field; `schema/` is authoritative. Short version: `refs[id]` (page, table, row,
printed `values`, unit, method, top); `nodes[]` (id, kind, section, parent/owner/anchor, amount in euros, ref, refCol,
cats, sources, prev, flags, `name_<lang>`); `flows[]`; `checks[]` (status pass/fail, cls error/rounding/null, bound);
`findings[]`; `kpis[]`; `tours[]`. Presentation (tabs, Sankey columns, categories, chunks, strings) is `dataset.json`.

## Front end facts worth knowing

- Tabs come from `dataset.json`: layouts `sankey`, `cards`, `ranking`, `checks`. Each tab's world is laid out once.
- Semantic zoom `levelOf(k)`: < 0.55 totals only; < 1.3 organisations by category + programme rows; ≥ 1.3 everything.
- Text: `txt()`/`txtLines()` in the engine draw counter-scaled text clipped to its box; overflow is recorded (tests read it).
- Data: `dist/` fetches `data/<chunk>.<hash>.json` on demand via the manifest in index.html; `dist-single/` has it inline.
  Chunk loading is async; actions return promises; `__canvas.idle()` waits for them.
- URL state: `#tab=…&node=…&flow=…&tour=…&step=…&lang=en&fmt=short`. Inside sandboxed iframes (about:srcdoc) the History
  API throws; the page detects that once and switches to an in-memory history with ←/→ buttons. Keep that.
- The controller commits with `flushSync` on purpose (camera code measures the tour bar right after a step).
- The panel is the selection: never add `sel`/`selFlow`/`hl` state; derive it in `state/selection.ts`.
- The engine does not import the store; it gets `view()` from the controller and reports clicks and zoom level back.
- Design: no external requests, no web fonts, system sans with tabular numerals; palette in `:root` CSS variables,
  category colours from `dataset.json`.

## Known findings (do not "fix" the data)

Listed in `docs/checks.md`. Highlights: Table 2 omits €12.0M donor grants that Table 1 counts; municipal ceilings exceed
municipal plans by €181,296; p.701 narrative growth 10.0% vs 9.7% in its own table; debt 22.0% vs 21.9% of GDP.

## Backlog / ideas (ask the owner before big changes)

- English translations for the remaining programme names (539 Albanian-only) and project names (Albanian-only by design so far).
- Municipality per-capita view: blocked — the PDF has no population data (rule 1). Only with the owner's explicit OK to add an external source, clearly labelled.
- A "download findings as CSV" button in the reconciliation dialog.
- Several datasets on one site (one folder per year plus a landing page; see docs/new-dataset.md).
- Optional custom domain on GitHub Pages (Settings → Pages; no CNAME file needed with Actions deployment).
- Possible later cleanup: refactor the normalize exec-chain into modules; `name_sq` → `name_<lang>` is already how the
  viewer reads it, but checks keep English in unsuffixed fields (ADR-003).

## Gotchas

- Scripts resolve paths through `pipeline/paths.py` (`BUDGET_DATASET`, `BUDGET_DATASET_DIR`); they run from any cwd. Node
  tools accept the same variables (and `DATASET`, `DATASET_DIR`).
- Re-running `normalize.py` renumbers `refs` ids, so always re-run snippets after it (`make data snippets`).
- Snippet JPEGs depend on the pdfium version (pixels change, content does not); they are excluded from the CI reproduction check.
- Table 1/1.1 are in € million with 1–2 decimals; everything else is in euros. Units are stored on every ref; amounts in nodes are always euros.
- Albanian letters ë/ç: search folds them (`fold()`); fold also when matching names in scripts (`fold_` in part 4).
- The PDF's annex copies of Tables 1/1.1 (pp.703–705) are identical to pp.29–33 apart from display rounding.
- Port 5173 may be in use by another local project; Vite picks the next free port.
