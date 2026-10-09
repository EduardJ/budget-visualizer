# ADR-004: A split build for GitHub Pages and a single-file build

## Status
Accepted

## Date
2026-10-09

## Context
The original page was one 15 MB HTML file: everyone downloaded all data and 5 MB of base64 page crops before seeing
anything. That single file was also a feature: it opens from disk and runs inside sandboxed iframes (`about:srcdoc`),
where nothing can be fetched and the History API throws.

## Decision
One codebase, two outputs from the same Vite plugin (`tools/vite-plugin-dataset.ts`):
- `dist/` (default): index.html carries a manifest; core data (~240 KB gzipped) loads at start; each other chunk loads the
  first time it is needed; snippets are JPEG files; every data file name carries a content hash.
- `dist-single/` (`--mode single`): every chunk and snippet inline, script and styles inline.

The viewer detects which one it is in (`app/src/data/source.ts`); everything else is identical. Loading is asynchronous
in both, applied in request order so the indexes are built the same way every time.

## Alternatives considered
- **Single file only.** Works on Pages, but a 15 MB first load for every visitor.
- **Split only.** Breaks offline use and sandboxed previews, which the owner uses.
- **Prefetch every chunk after start.** Faster tab switches, but ~1.3 MB compressed for every visitor, most of whom
  never open the project tables; chunks load in well under a second on demand.

## Consequences
- First load on Pages drops from 15 MB to about 370 KB compressed.
- Both builds are tested on every run (ADR-006).
- Content hashes make Pages' 10-minute cache safe across data updates.
