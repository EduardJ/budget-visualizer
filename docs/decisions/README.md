# Architecture decisions

One record per decision that would be expensive to reverse. Do not edit an accepted record to change the decision;
write a new one that supersedes it.

| # | Decision | Status |
|---|---|---|
| [001](ADR-001-vite-typescript-react.md) | Vite + TypeScript + React for the viewer | Accepted |
| [002](ADR-002-canvas-engine-outside-react.md) | The canvas engine stays imperative, outside React | Accepted |
| [003](ADR-003-data-contract-and-dataset-config.md) | data.json + dataset.json with JSON Schemas; the viewer is document-agnostic | Accepted |
| [004](ADR-004-split-and-single-file-builds.md) | A split build for GitHub Pages and a single-file build | Accepted |
| [005](ADR-005-dataset-folders-and-adapters.md) | One folder per dataset with its own adapter; committed, reproducible outputs | Accepted |
| [006](ADR-006-browser-tests-against-every-build.md) | Playwright tests in TypeScript against every build and a synthetic dataset | Accepted |
