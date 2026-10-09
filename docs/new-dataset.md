# Adding a dataset

A dataset is a folder under `datasets/` with a PDF, a `dataset.json` and a `data.json` (see [data-format.md](data-format.md)).
The viewer, the build and the generic tests work for any folder that validates. What differs between documents is the
**adapter**: the code that turns that PDF into `data.json`.

Pick the dataset for any command with `DATASET=<folder>` (or `DATASET_DIR=<path>` for a folder elsewhere):

```bash
DATASET=kosovo-2027 npm run validate
DATASET=kosovo-2027 npm run dev
make DATASET=kosovo-2027 extract data snippets verify
```

With a single folder under `datasets/` it is picked automatically; with several, `DATASET` is required.

## A. The next edition of the same law (e.g. Kosovo 2027)

The tables keep their structure from year to year; page numbers, column positions, years and some row labels move.

1. **Copy the folder** and drop the outputs:
   ```bash
   cp -R datasets/kosovo-2026 datasets/kosovo-2027
   rm -rf datasets/kosovo-2027/{raw,snippets,data.json,spotcheck.json} datasets/kosovo-2027/budget-2026.pdf
   cp ~/Downloads/budget-2027.pdf datasets/kosovo-2027/
   ```
   In `dataset.json` set `"id": "kosovo-2027"` and `"pdf": "budget-2027.pdf"`.

2. **Locate the tables.** For each table in `adapter/layout.py`, find its pages and read the column anchors:
   ```bash
   BUDGET_DATASET=kosovo-2027 .venv/bin/python pipeline/inspect_page.py 34
   #  303.6  Gjithesej Niveli Qendror 45,545@241 558,354,078@305 …   ← number@x of its right edge
   ```
   Each anchor is the right-edge x of the numbers in a column. Update `pages`, the `top`/`band` y-limits and `cols` per
   table. That file is the only place page ranges and anchors live.

3. **Extract** and read what came out:
   ```bash
   make DATASET=kosovo-2027 extract
   ```
   - The parsers stop with a `ValueError` naming the number and its x (`unplaced 1,234 at 812.4`) when a number is not
     near any anchor: fix that column's anchor or the table's `num_x`.
   - `parse_cap.py` prints `UNPARSED` lines it could not classify.
   - Open `raw/*.csv`: one row per printed line, check the row counts per table against the PDF.

4. **Move the years.** Column keys carry the year (`y2026`, `total_2026`, `spent_to_2025`, `cont_2026`, `new_2026`,
   `y2029plus`), in the parsers' column names, in `normalize*.py`, and in `dataset.json` (`panel`, `columns`, strings like
   `prevYear`, `s4`). Rename them deliberately; `grep -rn 2026 datasets/kosovo-2027` lists every place.

5. **Labels and pages in normalisation.** `normalize.py` finds Table 1/1.1 rows by their printed label
   (`'1.1 Të Hyra Tatimore'`) and lists every table's pages in `SOURCES`. `normalize_part3.py` and `normalize_part4.py`
   read specific pages (the narrative chapter, the fiscal-risk statement); those checks are about that year's text and
   need rewriting. A changed label fails loudly (`KeyError`), never silently.

6. **Build the data and check it:**
   ```bash
   make DATASET=kosovo-2027 data snippets verify
   DATASET=kosovo-2027 npm run validate
   DATASET=kosovo-2027 npm run dev
   ```
   `sq_text.py` stops the run if a new check or finding has no Albanian text: add it there.

7. **Presentation.** In `dataset.json` check the Sankey columns (node ids of revenue and financing lines that appear or
   disappear), the strings that cite tables and years, and the assumptions.

8. **Tests.** `generic.spec.ts` and `layout.spec.ts` run on any dataset. `interact.spec.ts` and `sandbox.spec.ts` are the
   kosovo-2026 scenario (specific ids, figures and texts); copy them into a `kosovo-2027` scenario with that year's
   figures, and make `isKosovo2026` in `tests/helpers.ts` select per dataset.

## B. A different document

Write an adapter that produces a `data.json` satisfying `schema/data.schema.json`. It can be any language; the Python
helpers in `pipeline/` are there to reuse:

| module | gives you |
|---|---|
| `pipeline/paths.py` | the dataset folder, its adapter folder and its PDF, from `BUDGET_DATASET` / `BUDGET_DATASET_DIR` |
| `pipeline/pdfutil.py` | `lines(page)`: printed lines with word positions; `lines_merged` for glyph-split numbers; `band_text` for text by x-range |
| `pipeline/exact.py` | exact decimal checks on printed tokens: `relation`, `rounds_to`, `interval`, `term_from` |
| `pipeline/snippets.py` | `render(refs, ids, pdf, out_dir)`: highlighted row crops |
| `pipeline/spotcheck.py` | re-read values with pdftotext and confirm them against their labels |
| `pipeline/inspect_page.py` | look at a page the way the parsers do |

What the viewer needs, at minimum:

- **refs** for every number, with the printed token in `values` and the page.
- **nodes** with `id`, `kind`, `amount`, `ref`, `refCol` and `name_<sourceLang>`; category nodes `cat:<id>` for every
  category in `dataset.json`.
- **flows** between nodes for whatever the Sankey shows (`kind: "hard"` when the document states it).
- **checks** and **findings**, with titles in every UI language (the unsuffixed `title` is English).
- `kpis` and `tours` may be empty arrays.

Then write `dataset.json`: the tabs that fit the document (a Sankey of where money comes from and goes, cards per
organisation, a ranking of projects, the checks), categories and colours, strings in each language. Start from
`tests/fixtures/minimal/`, a small synthetic dataset with three tabs, one language and a different currency; it is
built and tested on every run to prove the viewer has nothing specific to one document.

Add a `Makefile`-compatible adapter (`adapter/extract.py`, `normalize.py`, `snippets.py`, `spotcheck.py`) to get
`make extract data snippets verify` for free.

## More than one dataset on one site

Each build holds one dataset. To publish several (e.g. every year), build each into its own folder and add a landing page:

```bash
DATASET=kosovo-2026 npx vite build --outDir ../dist/2026
DATASET=kosovo-2027 npx vite build --outDir ../dist/2027
```

All paths are relative, so each folder works on its own. The workflow currently publishes one dataset; extend its build
step if you want this.
