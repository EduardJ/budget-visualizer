# Budget Visualizer

An interactive, zoomable map of a budget law: where the money comes from, where it goes and how it is spent, with
**every number linked to the page, table and row of the official PDF** it was printed in, and an exact audit of every
total the document prints. Albanian and English.

The first dataset is Kosovo's 2026 budget law (Ligji Nr. 10/L-001, Gazeta Zyrtare Nr. 4, 2 mars 2026, 728 pages).
The viewer is generic: another year of the same law, or another budget document, is a new folder under `datasets/`.

**Live:** `https://<user>.github.io/<repo>/` once deployed (see [Deploying](#deploying)).

## What it shows

- **Income and spending**: a Sankey from every revenue and financing line, through the budget, to central government,
  municipalities, interest and donor grants, and on to economic categories (wages, goods, subsidies, capital...).
- **Central government**: 50 institutions as cards, each down to programme and sub-programme, split by category and
  funding source.
- **Municipalities**: 38 cards down to sub-programme, with each municipality's revenue; sortable.
- **Capital projects**: the 150 largest of 2,975, with their multi-year amounts.
- **Findings**: 561 checks of the document's own arithmetic (407 exact, 95 off by rounding only, 59 arithmetic errors)
  and 993 findings, each linked to its pages.
- **Every figure opens its source**: table, page, the row as printed, the value as printed, a highlighted crop of the
  page, and a link to that page of the PDF. Copy a ready-made citation with one click.
- **Search** by name, amount (`1.2M`, `1,194,770,851`) or page (`p 45`); **guided tours** through the money trail;
  **filters** that dim without moving anything; shareable links for every view; works on phones; a single-file
  version that works offline.

## Rules the project keeps

1. **The PDF is the only source of numbers.** No outside figures, no estimates. If the PDF is wrong, it is shown as a finding, never "fixed".
2. **Every number has a source reference**: page, table, row, original label, the value exactly as printed, unit, method.
3. **No tolerance in checks.** A check passes only when the printed figures agree exactly. Failures are labelled
   *arithmetic error* (the gap is larger than rounding of the printed digits could produce) or *rounding only*; both are shown.
4. **Every user-facing text in every UI language**, including every check and finding. The build fails otherwise.
5. **Layout is identical at every zoom level.** Zoom only changes what is drawn; filters dim, never move.

## Requirements

| To | You need |
|---|---|
| run, build or deploy the site | Node 22.12 or newer (npm comes with it) |
| run the browser tests | the above, plus Playwright's Chromium: `npx playwright install chromium` |
| re-extract the data from the PDF | Python 3.9+, the packages in `requirements.txt`, and poppler (`pdftotext`) for `make verify` |

The extracted data is committed, so viewing, building and deploying never need Python.

## How to run

**Look at it locally**

```bash
git clone <this repository> && cd budget-visualizer
npm ci
npm run dev                         # opens on http://localhost:5173 (or the next free port); reloads on every change
```

**Build what gets published**

```bash
npm run build                       # dist/: the GitHub Pages site
npm run preview                     # serve dist/ at http://localhost:4173
npm run build:single                # dist-single/index.html: one file with everything inside, open it from disk
```

**Test everything** (what CI runs)

```bash
npx playwright install chromium     # once
npm run check                       # typecheck, validate the dataset, build all targets, browser tests
```

**Re-extract the data from the PDF** (only when the PDF or the extraction code changes)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
brew install poppler                # macOS; on Debian/Ubuntu: sudo apt install poppler-utils
make extract data snippets          # PDF -> raw/*.csv -> data.json -> snippets/*.jpg   (about 2 minutes)
make verify                         # re-read sampled values with a second extractor: expect 20/20, 13/13, 15/15
npm run check
```

Re-extraction is deterministic: on the same PDF it reproduces `raw/` and `data.json` byte for byte, and CI checks that.

## Commands

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with live reload |
| `npm run build` | `dist/`: the GitHub Pages build (index.html, JS, data chunks fetched on demand, page snippets, the PDF) |
| `npm run build:single` | `dist-single/index.html`: one self-contained file (works offline and in sandboxed iframes) |
| `npm run preview` | Serve `dist/` at http://localhost:4173 |
| `npm run validate` | Check the dataset against `schema/` and every cross-reference, without building |
| `npm run typecheck` | TypeScript |
| `npm test` | Build every target and run the browser tests against each |
| `npm run check` | typecheck + validate + `npm test`, what CI runs |
| `make extract data snippets` | PDF → `raw/*.csv` → `data.json` → `snippets/*.jpg` (Python pipeline) |
| `make verify` | Re-read sampled values with a second extractor (pdftotext) and confirm them |
| `make help` | All make targets; `DATASET=<folder>` picks the dataset (default `kosovo-2026`) |

## Repository layout

```
app/                       the viewer: Vite + TypeScript + React (canvas engine in app/src/canvas/)
datasets/kosovo-2026/      one document: the PDF, dataset.json (how to present it), data.json (what it says),
                           raw/ (CSV straight from the PDF), snippets/ (page crops), adapter/ (its extraction code)
pipeline/                  shared Python: PDF word positions, exact decimal arithmetic, snippet rendering, re-reading
schema/                    JSON Schemas of dataset.json and data.json, the contract between pipeline and viewer
tools/                     build tooling: dataset loading, validation, chunking (Vite plugin)
tests/                     Playwright browser tests, and a small synthetic second dataset
docs/                      documentation and architecture decisions
.github/workflows/         test on every pull request; test, re-extract and deploy to GitHub Pages on main
```

## Deploying

1. Push this folder to a GitHub repository, on the `main` branch.
2. In the repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Every push to `main` then tests everything, re-extracts the PDF to prove the committed data still matches it, and
   publishes `dist/` at `https://<user>.github.io/<repo>/`.

All paths are relative, so it works under any sub-path. Custom domains and other hosts (Netlify, Cloudflare Pages,
any static server): [docs/deploying.md](docs/deploying.md).

## How this was made

The source is the law as published in the Official Gazette, kept unchanged in `datasets/kosovo-2026/budget-2026.pdf`.
Every number goes through the same steps, and each step can be re-run and checked:

1. **Extraction.** The parsers read the word coordinates of each page (pdfplumber). A number belongs to the column whose
   header it lines up with on the right edge, and the parsers write one CSV row per printed line (`raw/`). Nothing is
   typed in by hand; the page ranges and column positions of every table are in one file, `adapter/layout.py`.
2. **Normalisation.** The rows become nodes (revenue lines, institutions, programmes, municipalities, projects), flows
   between them, and a source reference for every figure (`data.json`).
3. **Audit.** Every relation the document prints is recomputed with exact decimal arithmetic on the digits as printed:
   totals against their lines in every column and year, the same figure across tables, percentages in the text against
   the tables, amounts cited in the law's articles. Every mismatch is kept as a finding.
4. **Verification.** A second extractor (poppler's pdftotext) re-reads the 20 largest values, 20 random ones and every
   flagged one and confirms each against its row label. CI re-runs the extraction and fails if the result differs from
   the committed data.

The software was built with **Claude** (Anthropic's AI model) working as a coding agent in **Claude Code**, directed by
the project's owner. The first version was one HTML file with the Python pipeline; its rules and findings are recorded in
[CLAUDE.md](CLAUDE.md), which is also the guide any coding agent reads before changing the project. This version was
rebuilt from it with Claude Opus 5.5 into the reusable app described here. Before the rebuild, the original's behaviour
was recorded: every panel's text for every node in both languages and every flow, every tour step, the headline
figures, the reconciliation, search results, layouts and canvas screenshots. The new build was then compared against
that record and matched, and the original's tests pass on it unchanged. The decisions behind the structure are in
[docs/decisions/](docs/decisions/).

## Make something similar

> **Generated with [Claude Code](https://claude.com/claude-code).** The code, the extraction pipeline, the tests and
> this documentation were generated by Claude, Anthropic's AI model, working in Claude Code from prompts like the ones
> below, under the owner's direction. The numbers themselves come only from the PDF, through the steps above.

The prompt below is what to give a coding agent (Claude Code or similar) to build a page like this for another budget
document. Start in an empty folder with the PDF in it, replace the `[...]` parts, and let it work phase by phase. The
rules section matters most: it is what keeps the numbers trustworthy.

```text
Build a static budget visualizer that lets anyone trace every [euro / dollar / ...] of [document name, e.g. "the 2027
budget law of X"] ([file].pdf, [N] pages) from where the money comes from to where it is spent, and that audits the
document's own arithmetic. Interface in [language 1] (default) and [language 2].

Non-negotiable rules:
1. The PDF is the only source of numbers. No outside figures, no estimates. If the PDF is inconsistent, show the
   inconsistency as a finding; never correct it.
2. Every number on screen has a source reference: page, table, row label as printed, the value exactly as printed,
   unit, and whether it was parsed or computed. Add a check that counts amounts without a reference; it must be 0.
3. No tolerance in checks. Use exact decimal arithmetic on the printed digits. A check passes only when the printed
   figures agree exactly. Label a failure "arithmetic error" when the gap is larger than rounding of the printed
   digits could produce (or two prints of the same figure differ), and "rounding only" when it is within half a unit
   of the last printed digit of each figure involved. Show both; never hide or merge failures.
4. Every user-facing text, including every check and finding, in both languages; fail the build if one is missing.
5. Layout is identical at every zoom level: zoom only changes what is drawn, filters dim and never move anything,
   and text never leaves its box.
6. After every change, run the tests and an independent re-read of sampled values with a second PDF extractor, and
   report the actual numbers.

Extraction:
- Start with an inventory: every table, its pages, unit and what it covers. Show it to me before going further.
- Extract with word coordinates (pdfplumber). Assign each number to a column by the x of its right edge against the
  column headers. Keep every page range and column position in one layout file. Never read numbers by eye.
  Write one CSV row per printed line.
- Write a JSON Schema for the normalised data first: nodes (revenue lines, totals, institutions, programmes,
  sub-programmes, local governments, projects), flows between them, source references, checks, findings, headline
  figures and guided tours. Then normalise the CSVs into it.
- Check every printed relation: totals against their lines in every column and year, the same figure across tables,
  figures in the narrative text against the tables, amounts cited in the law's articles.
- Re-running the pipeline on the same PDF must reproduce the data byte for byte.

The page:
- Vite + TypeScript + React, fully static. Two builds: one for GitHub Pages (relative paths, data split into
  content-hashed chunks loaded on demand) and one single HTML file that works offline and inside sandboxed iframes.
- The map on a canvas, not in React: a Sankey from revenue and financing through the budget to destinations and
  economic categories; one card per institution and per local government down to sub-programme; the largest capital
  projects; every check and finding. Three levels of semantic zoom.
- A details panel for every node and flow: amount, shares, previous year, and its source with the printed row, a
  highlighted crop of the PDF page and a link to that page; a button that copies a citation.
- Search by name, amount ("1.2M") or page ("p 45"); guided tours along the money trail; filters by category,
  government level and size; a reconciliation dialog listing every check and finding with filters for errors,
  rounding, passed and notes. Every view has a shareable URL; browser back and forward work; usable on a phone.
- Everything specific to this document (tabs, Sankey columns, categories, labels) lives in a config file, not in code.

Quality:
- Playwright tests: no overlapping boxes, no text overflow at five zoom levels, layout identical across zoom, a full
  user session (clicks, ribbons, citations, search, tours, keyboard, deep links, back/forward, phone), the
  sandboxed-iframe case.
- A GitHub Actions workflow that runs the tests, re-extracts the PDF and fails if the committed data differs, then
  deploys to GitHub Pages.
- Documentation: README, architecture, data format, how to add a dataset, how the checks work, and records of the
  main decisions. Write a CLAUDE.md with the rules above for future agents.

Work in phases and stop after each one to show me the results with real numbers: (1) inventory and schema,
(2) extraction, with row counts per table, (3) normalised data and checks, with pass / rounding / error counts,
(4) the page, (5) tests, documentation and deployment.
```

**Adding the next edition of the same law to this repository** is shorter, because the rules, the viewer and the
pipeline already exist:

```text
Read CLAUDE.md and docs/new-dataset.md first. Add a dataset datasets/kosovo-[year] from [file].pdf, following part A of
docs/new-dataset.md: copy the 2026 folder, find the table pages and column anchors with pipeline/inspect_page.py,
update adapter/layout.py, move the year columns, fix the row labels and page-specific checks, and add the Albanian
text for every new check. Keep every rule in CLAUDE.md. Report the row counts per table, the check counts (exact,
rounding only, arithmetic error), the make verify results and the test results, and list every finding that is new
compared with 2026.
```

## Disclaimer

This is an independent tool, not an official publication of the Government of Kosovo or its Ministry of Finance.
Figures are shown exactly as printed in the law; where the document contradicts itself, the page shows the
contradiction instead of choosing a value. The checks are mechanical comparisons of printed figures, not an audit
opinion. Check the PDF before citing a number; every figure links to its page.

## Documentation

- [Architecture](docs/architecture.md): how the pieces fit, from PDF to pixels
- [Data format](docs/data-format.md): `data.json` and `dataset.json`, field by field
- [Adding a dataset](docs/new-dataset.md): next year's budget law, or a different document
- [The checks](docs/checks.md): how the audit works and how to add a check
- [Development](docs/development.md): tests, verification, debugging
- [Deploying](docs/deploying.md)
- [Decisions](docs/decisions/): why it is built this way
- [Changelog](CHANGELOG.md)
