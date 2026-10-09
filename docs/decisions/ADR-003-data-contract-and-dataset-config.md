# ADR-003: data.json + dataset.json with JSON Schemas; the viewer is document-agnostic

## Status
Accepted

## Date
2026-10-09

## Context
To reuse the viewer for another year or another document, everything specific to one document must be data, and
mistakes in that data must be caught before a page is published (rule 2: every number has a source; rule 4: every text
in every language).

## Decision
Two files per dataset:
- `data.json`: what the document says (nodes, flows, refs, checks, findings, headline figures, tours), produced by the
  adapter, unchanged in shape from the original pipeline;
- `dataset.json`: how to present it (tabs and their layouts, Sankey columns, categories and colours, chunks, panel
  columns, every document-specific string, assumptions), written by hand.

Both have JSON Schemas in `schema/`. `tools/dataset.ts` validates them on every build and in `npm run validate`, and then
checks what a schema cannot: every ref, node and flow referenced exists, every text exists in every UI language, every
tab's kind exists. The build fails on any error. Localised fields follow `<field>_<lang>`.

## Alternatives considered
- **One merged file.** Mixes generated data with hand-written presentation; regenerating data would overwrite edits.
- **Presentation as TypeScript per dataset.** Typed, but puts document knowledge back into code and needs a code change
  per dataset.
- **Change data.json's shape at the same time** (e.g. `names: {sq, en}`). Cleaner, but would break the byte-identical
  check against the original pipeline that proves nothing changed; possible later as its own decision.

## Consequences
- A synthetic second dataset (`tests/fixtures/minimal`: English only, dollars, three different tabs, no chunks) builds
  and passes the generic tests, which proves the viewer has nothing Kosovo-specific left.
- `name_sq`/`title_sq` field names are historical; the unsuffixed `title`/`note` of checks are English. Documented in
  docs/data-format.md.
- Built-in interface text exists for sq and en (`app/src/strings.json`); a new UI language needs a translation there or
  overrides in the dataset.
