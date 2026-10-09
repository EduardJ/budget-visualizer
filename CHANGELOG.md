# Changelog

## 2.0.0 (2026-10-09)

Rebuilt as a reusable app. Same numbers, same checks, same behaviour, verified against the previous build: identical
layout on every tab, identical panel text for every node (both languages) and every flow, identical canvas pixels, and
the original test suites passing unchanged.

### Changed
- Renamed to **Budget Visualizer** across the interface, the page title and the data; the tours button is now
  "Ture të udhëzuara / Guided tours".
- The viewer is a Vite + TypeScript + React app (`app/`); the canvas engine is a typed module. See docs/decisions/.
- Nothing in the viewer is specific to Kosovo 2026 any more: tabs, Sankey columns, categories, colours, labels and
  assumptions come from `datasets/<id>/dataset.json`, validated against `schema/` on every build.
- GitHub Pages build (`dist/`): data in content-hashed chunks fetched on demand, page snippets as image files. First
  load is about 370 KB compressed instead of 15 MB. The single-file build remains (`npm run build:single`).
- The pipeline is split into shared helpers (`pipeline/`) and the Kosovo adapter (`datasets/kosovo-2026/adapter/`);
  every page range and column anchor is in `adapter/layout.py`. Outputs are byte-identical to before.
- Tests are Playwright in TypeScript and run against both builds and a synthetic second dataset.
- CI (`.github/workflows/pages.yml`): tests every pull request; on `main` it also re-extracts the PDF, fails if the
  committed data differs, and deploys to GitHub Pages.

### Fixed
- Clicking a ribbon missed on screens with a device pixel ratio of 2 (most laptops and phones): the hit test divided the
  click position by the pixel ratio twice.
- Opening the capital-projects tab directly (or by deep link) showed no "run by" organisation, because those names
  lived in data chunks that were not loaded yet.
- A from-scratch rebuild (`make extract data` with an empty `raw/`) failed: `raw/org_names_annex1.json`, the full
  institution names from Annex 1, was committed but produced by no script. `adapter/parse_annex_names.py` now reads it
  from the PDF by character position and reproduces the committed file byte for byte.
- `make extract` creates `raw/` when it is missing.

### Added
- `npm run validate`: schema and cross-reference validation of a dataset.
- `pipeline/inspect_page.py`: a page printed the way the parsers see it, with each number's column anchor, for
  porting to a new edition.
- Documentation in `docs/`: architecture, data format, adding a dataset, the checks, development, deploying, and
  decision records.

## 1.0.0

Single-file viewer of the Kosovo 2026 budget law with the exact audit (561 checks; 407 exact, 95 rounding only,
59 arithmetic errors).
