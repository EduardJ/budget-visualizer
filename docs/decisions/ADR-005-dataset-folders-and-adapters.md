# ADR-005: One folder per dataset with its own adapter; committed, reproducible outputs

## Status
Accepted

## Date
2026-10-09

## Context
Extraction is inherently document-specific: page ranges, column x-positions, row labels, the narrative claims that are
checked. A "generic PDF budget parser" would be a research project; what can be shared is the machinery (word
positions, exact decimal arithmetic, snippet rendering, re-reading with a second extractor).

## Decision
- `datasets/<id>/` holds one document: the PDF, `dataset.json`, `data.json`, `raw/`, `snippets/`, and `adapter/` with
  that document's extraction and normalisation code.
- `pipeline/` holds the shared Python (`paths`, `pdfutil`, `exact`, `snippets`, `spotcheck`, `inspect_page`).
- Every page range and column anchor of the Kosovo parsers is in `adapter/layout.py`, the first file to change for a
  new edition.
- Outputs are committed, so building the site needs no Python. CI re-runs `make extract data` on every push and fails if
  `raw/` or `data.json` change: the committed data is always exactly what the PDF produces.

## Alternatives considered
- **One configurable parser for every document.** Tables differ in structure, not only in position; the configuration
  would become a programming language.
- **Run the pipeline only in CI, do not commit outputs.** Slower builds, Python and poppler in every build, and no reviewable
  diff of the data when the extraction changes.
- **Keep a flat `scripts/` folder.** Cannot hold a second document.

## Consequences
- A new edition starts as a copy of the folder (docs/new-dataset.md); code shared across editions is copied, not
  abstracted, until a second edition shows what really stays the same.
- The move was verified byte-identical: every raw CSV, data.json, every snippet JPEG and the `make verify` output.
- Snippet JPEGs depend on the pdfium version and are not part of the CI reproduction check.
