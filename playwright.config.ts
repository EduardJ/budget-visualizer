import { defineConfig } from '@playwright/test';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const file = (p: string) => pathToFileURL(resolve(p)).href;

// generic.spec and layout.spec hold for any dataset; interact.spec and sandbox.spec are the kosovo-2026 scenario.
// Each runs against the GitHub Pages build (dist/, served), the single-file build (dist-single/, from disk), and
// generic + layout also against a synthetic second dataset (dist-fixture/). `npm test` builds all three first.
export default defineConfig({
  testDir: 'tests',
  timeout: 240_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: { viewport: { width: 1440, height: 900 } },
  webServer: { command: 'npx vite preview --port 4173 --strictPort', url: 'http://localhost:4173/', reuseExistingServer: !process.env.CI },
  projects: [
    { name: 'pages', use: { baseURL: 'http://localhost:4173/' }, testIgnore: /sandbox/ },
    { name: 'single-file', use: { baseURL: file('dist-single/index.html') } },
    { name: 'fixture', use: { baseURL: file('dist-fixture/index.html') }, testMatch: /(generic|layout)\.spec/, metadata: { datasetDir: 'tests/fixtures/minimal' } },
  ],
});
