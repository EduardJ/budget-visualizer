import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { HtmlTagDescriptor, Plugin } from 'vite';
import type { Manifest } from '../app/src/types.ts';
import { bundle, datasetDir, jsonForHtml, loadDataset, validate, type Bundle, type Dataset } from './dataset.ts';

const LOADING: Record<string, string> = { sq: 'Duke ngarkuar…', en: 'Loading…' };

/**
 * Puts one dataset into the page.
 *  split  (default, for GitHub Pages): data/<chunk>.<hash>.json and snippets/<rid>.<hash>.jpg next to index.html,
 *         found through a manifest in the page; content-hashed names so a new dataset never mixes with cached files.
 *  single (vite build --mode single): every chunk and snippet inline, so index.html works offline and in sandboxed iframes.
 * The PDF is copied next to index.html in both, because every source reference links to <pdf>#page=N.
 */
export function datasetPlugin({ single }: { single: boolean }): Plugin[] {
  let ds: Dataset, out: Bundle, files = new Map<string, Buffer>(), manifest: Manifest;

  const prepare = () => {
    ds = loadDataset(datasetDir());
    const v = validate(ds);
    for (const w of v.warnings) console.warn(`[dataset] warning: ${w}`);
    if (v.errors.length) throw new Error(`[dataset] ${ds.dir} is not valid:\n  ${v.errors.slice(0, 40).join('\n  ')}${v.errors.length > 40 ? `\n  … ${v.errors.length - 40} more` : ''}`);
    out = bundle(ds);
    files = new Map();
    const put = (dir: string, name: string, ext: string, buf: Buffer) => {
      const p = `${dir}/${name}.${createHash('sha256').update(buf).digest('hex').slice(0, 10)}.${ext}`;
      files.set(p, buf);
      return p;
    };
    manifest = { core: '', chunks: {}, snips: {} };
    if (!single) {
      manifest.core = put('data', 'core', 'json', Buffer.from(JSON.stringify(out.core)));
      for (const [k, c] of Object.entries(out.chunks)) manifest.chunks[k] = put('data', k, 'json', Buffer.from(JSON.stringify(c)));
      for (const [rid, buf] of ds.snippets) manifest.snips[rid] = put('snippets', rid, 'jpg', buf);
    }
  };

  const html = (src: string) => {
    const C = ds.config, lang = C.langs[0], S = C.strings[lang] ?? {};
    const text = (v: unknown) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    return src
      .replace('%LANG%', text(lang))
      .replace('%TITLE%', text(S.documentTitle ?? S.title))
      .replace('%DESCRIPTION%', text(S.sub))
      .replace('%LOADING%', text(S.loading ?? LOADING[lang] ?? LOADING.en));
  };

  const dataTags = (): HtmlTagDescriptor[] => {
    const tag = (id: string, v: unknown): HtmlTagDescriptor => ({ tag: 'script', attrs: { type: 'application/json', id }, children: jsonForHtml(v), injectTo: 'body' });
    const tags = [tag('d-config', ds.config)];
    if (single) {
      tags.push(tag('d-core', out.core));
      for (const [k, c] of Object.entries(out.chunks)) tags.push(tag('d-' + k, c));
      tags.push(tag('d-snips', Object.fromEntries([...ds.snippets].map(([rid, b]) => [rid, 'data:image/jpeg;base64,' + b.toString('base64')]))));
    } else {
      tags.push(tag('d-manifest', manifest));
      tags.push({ tag: 'link', attrs: { rel: 'preload', href: manifest.core, as: 'fetch', crossorigin: '' }, injectTo: 'head' });
    }
    return tags;
  };

  const main: Plugin = {
    name: 'budget-dataset',
    buildStart() {
      prepare();
      for (const f of ['dataset.json', 'data.json']) this.addWatchFile(join(ds.dir, f));
    },
    configureServer(server) {
      prepare();
      server.watcher.add([join(ds.dir, 'dataset.json'), join(ds.dir, 'data.json'), join(ds.dir, 'snippets')]);
      server.watcher.on('change', f => {
        if (!f.startsWith(ds.dir)) return;
        try { prepare(); server.ws.send({ type: 'full-reload' }); } catch (e) { console.error(String(e)); }
      });
      server.middlewares.use((req, res, next) => {
        const path = decodeURIComponent((req.url ?? '').split(/[?#]/)[0]).replace(/^\/+/, '');
        const body = files.get(path) ?? (path === ds.config.pdf ? readFileSync(ds.pdf) : null);
        if (!body) return next();
        res.setHeader('Content-Type', path.endsWith('.json') ? 'application/json' : path.endsWith('.jpg') ? 'image/jpeg' : 'application/pdf');
        res.end(body);
      });
    },
    transformIndexHtml: { order: 'pre', handler: src => ({ html: html(src), tags: dataTags() }) },
    generateBundle() {
      for (const [fileName, source] of files) this.emitFile({ type: 'asset', fileName, source });
      this.emitFile({ type: 'asset', fileName: ds.config.pdf, source: readFileSync(ds.pdf) });
    },
  };

  // single-file build: replace the emitted script and stylesheet links with their contents
  const inline: Plugin = {
    name: 'budget-inline',
    enforce: 'post',
    apply: () => single,
    generateBundle(_, bundle) {
      const page = Object.values(bundle).find(o => o.type === 'asset' && o.fileName.endsWith('.html'));
      if (!page || page.type !== 'asset') return;
      let src = String(page.source);
      for (const [name, o] of Object.entries(bundle)) {
        const esc = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        if (o.type === 'chunk') {
          const re = new RegExp(`<script type="module"[^>]*src="[^"]*${esc}"[^>]*></script>`);
          if (!re.test(src)) continue;
          src = src.replace(re, () => `<script type="module">${o.code.replace(/<\/script/gi, '<\\/script')}</script>`);
          delete bundle[name];
        } else if (name.endsWith('.css')) {
          const re = new RegExp(`<link rel="stylesheet"[^>]*href="[^"]*${esc}"[^>]*>`);
          if (!re.test(src)) continue;
          src = src.replace(re, () => `<style>${String(o.source)}</style>`);
          delete bundle[name];
        }
      }
      page.source = src;
    },
  };

  return [main, inline];
}
