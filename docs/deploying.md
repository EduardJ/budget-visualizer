# Deploying

`npm run build` writes a static site to `dist/`:

```
dist/
  index.html                     page shell, dataset config, data manifest (~32 KB)
  assets/index-<hash>.js, .css   the viewer (~93 KB gzipped)
  data/core.<hash>.json          loaded at start (~240 KB gzipped)
  data/<chunk>.<hash>.json       loaded the first time a tab or node needs them
  snippets/<rid>.<hash>.jpg      page crops shown in the details panel
  budget-2026.pdf                every "Open in PDF" link points here (#page=N)
```

Every path is relative and every data file is content-hashed, so the folder can be served from any host and any
sub-path, and a new build never mixes with files cached from an old one.

## GitHub Pages (set up)

1. Create a repository on GitHub and push this folder to `main`.
2. Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Every push to `main` runs `.github/workflows/pages.yml`:
   - **viewer**: `npm ci`, Playwright's Chromium, `npm run check` (typecheck, dataset validation, all three builds, all
     browser tests), then uploads `dist/` as the Pages artifact. Screenshots and the single-file build are kept as run
     artifacts.
   - **pipeline**: installs Python and poppler, re-extracts the PDF (`make extract data`), fails if `raw/` or
     `data.json` differ from what is committed, and runs `make verify`.
   - **deploy**: only when both pass, publishes to `https://<user>.github.io/<repo>/`.
   Pull requests run the first two jobs only.

Size limits are not a concern: GitHub Pages allows 1 GB per site and 100 MB per file; the largest file here is the
4.8 MB PDF.

### Custom domain

Settings → Pages → Custom domain, then add the DNS record GitHub shows (a `CNAME` to `<user>.github.io` for a
subdomain). With Actions deployment no `CNAME` file is needed in the build.

## Other static hosts

Netlify, Cloudflare Pages, Vercel: build command `npm run build`, output directory `dist`, Node 22. Or upload `dist/` to
any web server. Serve `.json` with gzip or brotli; most hosts do by default.

## The single file

`npm run build:single` writes `dist-single/index.html` (about 15 MB) with all data, snippets, script and styles inline,
plus the PDF next to it. It needs no server: open it from disk, send it as an attachment, or embed it where fetching is
not possible (a sandboxed `srcdoc` iframe). CI attaches it to every run as the `single-file-build` artifact.
