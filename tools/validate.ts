// npm run validate [-- <dataset folder>]: check a dataset against schema/ and the cross-references, without building.
import { resolve } from 'node:path';
import { bundle, datasetDir, loadDataset, validate } from './dataset.ts';

const dir = process.argv[2] ? resolve(process.argv[2]) : datasetDir();
const ds = loadDataset(dir);
const { errors, warnings } = validate(ds);
for (const w of warnings) console.log('warning:', w);
for (const e of errors) console.log('error:  ', e);
if (errors.length) {
  console.log(`\n${dir}: ${errors.length} error(s)`);
  process.exit(1);
}
const b = bundle(ds);
const mb = (v: unknown) => (JSON.stringify(v).length / 1e6).toFixed(2);
const D = ds.data;
console.log(`${dir}: valid`);
console.log(`  ${D.nodes.length} nodes, ${D.flows.length} flows, ${Object.keys(D.refs).length} refs, ${D.checks.length} checks, ${D.findings.length} findings, ${D.tours.length} tours, ${ds.snippets.size} snippets`);
console.log(`  chunks (MB): ${[['core', b.core] as const, ...Object.entries(b.chunks)].map(([k, c]) => `${k} ${mb(c)}`).join(', ')}`);
