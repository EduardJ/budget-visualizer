# Development

```bash
npm ci                     # once
npm run dev                # viewer with live reload; edits to dataset.json / data.json reload the page too
```

## Verification after every change

Run all of it, report the actual numbers, and look at the screenshots in `tests/shots/<project>/`.

```bash
npm run check              # typecheck, validate the dataset, build dist/ + dist-single/ + dist-fixture/, browser tests
make verify                # only when data changed: pdftotext re-read of top 20 / 20 random / every flagged value
```

Expected today:

| suite | expected |
|---|---|
| `layout.spec` (pages, single-file, fixture) | every tab `[identical, 0 overlaps, fit shows all, 0 text overflow]` = `[true, 0, true, 0]` |
| `generic.spec` | 40/40 on kosovo-2026 (both builds), 23/23 on the fixture |
| `interact.spec` (pages, single-file) | 64/64 |
| `sandbox.spec` (single-file) | 8/8 |
| `make verify` | `top20: 20/20`, `random20: 13/13`, `flagged: 15/15` confirmed |

`npm test` builds first; `npm run test:only` reruns the browser tests on the existing builds.
`npx playwright test --project=pages tests/interact.spec.ts` runs one spec on one build.

## The tests

Playwright, in `tests/`, each spec run against up to three builds (`playwright.config.ts`):

- **pages**: `dist/` served by `vite preview`, data fetched in chunks, like GitHub Pages;
- **single-file**: `dist-single/index.html` opened from disk;
- **fixture**: a synthetic second dataset (`tests/fixtures/minimal/`) as a single file.

| spec | what it holds |
|---|---|
| `layout.spec.ts` | per tab: no overlaps, no counter-scaled text leaving its box at five zoom levels, layout identical across zoom, "fit" shows the whole world |
| `generic.spec.ts` | for any dataset, with ids and texts from that dataset: tabs, panels and their PDF citations, languages, search, reconciliation, tours, deep links |
| `interact.spec.ts` | the kosovo-2026 user session: clicks, ribbons, citations, search, toggles, filters that dim without moving, tours, keyboard, back/forward, deep links, mobile bottom sheet, high-density screens |
| `sandbox.spec.ts` | the single file inside a sandboxed `srcdoc` iframe: runs without errors, in-app back/forward, Albanian by default |

Tests drive the page through `window.__canvas` (`app/src/testHooks.ts`): `S` (state and camera), `L` (current layout),
`switchTab`, `showNode`, `showFlow`, `startTour`, `tourGo`, `setZoom`, `setCamera`, `fitAll`, `overlaps()`,
`textOverflow()`, `drawnText()`, `layoutSignature()`, `screenOf(id)`, `hit(x, y)`, `loaded()`, `idle()`. Actions return
promises that settle once data is loaded and the DOM is updated; prefer `idle()` over fixed waits.

## Pipeline changes

The pipeline is deterministic: re-running it on the same PDF must reproduce `raw/` and `data.json` byte for byte (CI checks
this). After changing extraction or normalisation:

```bash
make extract data snippets
git diff --stat datasets/                 # the change should be exactly what you meant
npm run check && make verify
```

`normalize.py` renumbers every ref id, so always regenerate `snippets/` after it. Snippet JPEGs depend on the pdfium
version: regenerating them on another machine changes pixels, not content.

## Gotchas

- Albanian letters: search folds diacritics (`fold()` in `app/src/format.ts`); fold also when matching names in
  scripts (`fold_` in `normalize_part4.py`).
- Tables 1/1.1 are in € million with 1–2 decimals; everything else in euros. Amounts in nodes are always euros; the
  printed unit is on each ref.
- The PDF's annex copies of Tables 1/1.1 (pp.703–705) are identical to pp.29–33 apart from display rounding.
- The canvas engine never reads the store: it draws the controller's `view()`; anything that changes what is drawn
  goes through a controller action, which marks the engine dirty.
- `flushSync` in the controller is deliberate: the camera code measures the panel and the tour bar right after a
  selection. Do not call controller actions during a React render.
- Port 5173 may be taken by another project; Vite picks the next free port and prints it.
