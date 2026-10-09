# ADR-006: Playwright tests in TypeScript against every build and a synthetic dataset

## Status
Accepted

## Date
2026-10-09

## Context
The original tests were three Python Playwright scripts against the single HTML file: layout invariants, a 59-step
user session, and the sandboxed-iframe case. They were the contract for the rewrite. With two builds and more than one
dataset, the same checks have to run against each.

## Decision
`@playwright/test` in TypeScript (`tests/`), three projects: `pages` (`dist/` served by `vite preview`), `single-file`
(`dist-single/` from disk) and `fixture` (the synthetic dataset). Specs:
- `layout.spec` and `generic.spec` hold for any dataset and take ids and texts from the dataset under test;
- `interact.spec` and `sandbox.spec` are the kosovo-2026 scenario, ported check for check from the Python suites (plus
  new checks for high-density screens and the projects tab), skipped for other datasets.

## Alternatives considered
- **Keep the Python tests.** They need a second Playwright install, and only test the single file.
- **Unit tests only.** The invariants that matter (no overlap, no text overflow, identical layout across zoom, URL
  state, sandboxed iframes) are only observable in a browser.

## Consequences
- One command (`npm test`) for the viewer; CI runs it on every pull request.
- The port surfaced two bugs of the original that the old tests could not see, now covered: ribbon clicks missed on
  screens with device pixel ratio 2, and the projects tab showed no owner names when opened directly.
