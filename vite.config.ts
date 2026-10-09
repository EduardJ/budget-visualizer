import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { datasetPlugin } from './tools/vite-plugin-dataset.ts';

// `vite build` → dist/ for GitHub Pages (data fetched in chunks);
// `vite build --mode single` → dist-single/index.html with everything inline (offline, sandboxed iframes);
// `vite build --mode fixture` → dist-fixture/, the synthetic test dataset as a single file.
// The dataset is datasets/$DATASET (or $DATASET_DIR); with one dataset it is picked automatically.
export default defineConfig(({ mode }) => {
  const fixture = mode === 'fixture', single = mode === 'single' || fixture;
  if (fixture) process.env.DATASET_DIR = 'tests/fixtures/minimal';
  return {
    root: 'app',
    base: './',
    publicDir: false,
    plugins: [react(), ...datasetPlugin({ single })],
    build: {
      outDir: fixture ? '../dist-fixture' : single ? '../dist-single' : '../dist',
      emptyOutDir: true,
      target: 'es2022',
      cssCodeSplit: !single,
      modulePreload: single ? false : undefined,
      assetsInlineLimit: single ? Number.MAX_SAFE_INTEGER : 4096,
      reportCompressedSize: false,
    },
    preview: { port: 4173, strictPort: true },
  };
});
