# ADR-001: Vite + TypeScript + React for the viewer

## Status
Accepted

## Date
2026-10-09

## Context
The viewer was one 93 KB JavaScript file inlined with 15 MB of data into a single HTML page by a Python script. It
worked and was well tested, but it was hard to reuse: every Kosovo-2026 specific (tab list, Sankey columns, table names
in labels, years) was written into the engine, the DOM was built from template strings escaped by hand in nine places,
and there was no type checking. The owner wants it reusable for future editions of the law and for other budget
documents, maintained by more than one person, and hosted on GitHub Pages.

## Decision
A Vite project in `app/` written in TypeScript (strict). The DOM around the canvas (header, search, tabs, headline
figures, details panel, reconciliation dialog, tour bar, filters) is React 19 components. One small external store
(`useSyncExternalStore`) holds UI state; a controller is the only writer.

## Alternatives considered
- **Keep plain JavaScript, split into modules.** Least change, but keeps hand-escaped HTML strings and no types on a data
  model with 50 optional fields; the panel is the part that changes most.
- **Preact.** Same API at a tenth of the size. React's extra ~60 KB gzipped is small next to 240 KB of core data, and
  React is what most contributors know; Preact remains a drop-in option (`preact/compat`) if size ever matters.
- **Svelte / Vue.** Fine tools, smaller pool of people who already know them for this team; no advantage for a canvas-first page.
- **Next.js or another SSR framework.** Nothing to render on a server; the site is static and must also work as one file
  offline.

## Consequences
- Types for the whole data model (`app/src/types.ts`), checked with `tsc --noEmit`.
- Automatic escaping in the panel; no `innerHTML`.
- A Node toolchain is required to build the site (Python is only needed to re-extract data).
- The port was verified to be behaviour-identical: same layout signature on every tab, identical panel text for every
  node in both languages and every flow, identical canvas pixels, and the original Python test suites passing on the new build.
