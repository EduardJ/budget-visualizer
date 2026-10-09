# ADR-002: The canvas engine stays imperative, outside React

## Status
Accepted

## Date
2026-10-09

## Context
The map draws up to ~1,600 boxes per tab, ~60 ribbons and their labels, at 60 fps while the camera pans and zooms, with
semantic zoom (what is drawn depends on the scale) and counter-scaled text that must never leave its box. The camera
changes on every frame.

## Decision
`app/src/canvas/` is plain TypeScript: `layout.ts` builds each tab's world once in world units, `engine.ts` owns the
camera, the draw loop, text fitting and hit testing. React never re-renders because the camera moved. The engine reads
UI state from the store at draw time and redraws on the next frame after any change; React components call the
controller, which calls the engine for camera moves.

## Alternatives considered
- **SVG rendered by React.** Thousands of elements re-rendered on zoom; measuring and clipping text per element is slow.
- **react-konva / pixi-react.** Adds a scene graph and a dependency for what is a few hundred lines of direct 2D canvas
  code; no gain in correctness, and the tests measure text overflow on our own draw calls.
- **d3.** Useful for the Sankey maths, but the layout is custom (columns from config, stacked ribbons, fixed world) and
  already exact.

## Consequences
- The engine has no React dependency and could be reused by another UI.
- Two update paths exist (store → React re-render, store → engine dirty flag); the controller is the single place that
  changes state, which keeps them consistent.
- The controller commits state with `flushSync`, because the camera code measures the panel and tour bar right after a
  selection (see docs/architecture.md).
