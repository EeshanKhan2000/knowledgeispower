# Dashboard

Static Next.js (App Router, `output: 'export'`) + Tailwind CSS site for the scp-graphfs-mcp benchmark.
`npm run build` writes plain HTML/CSS/JS to `dashboard/out/`.

## Build

```bash
cd dashboard
npm ci
npm run build                                    # reads ../results (default)
RESULTS_DIR=../benchmarks/_quick_out npm run build   # develop against the quick run
```

Preview locally: `python3 -m http.server 4173 -d out` (or `npx serve out`), then open http://localhost:4173/.

Environment variables (all read at build time only):

| variable | default | purpose |
|---|---|---|
| `RESULTS_DIR` | `../results` | directory with `*.json` + `discordant_subunits.csv` from `benchmarks/run.py` |
| `GLOSSARY_FILE` | `../docs/glossary.json` | override only for testing the glossary UI with a fixture |
| `NEXT_BASE_PATH` | empty | set (e.g. `/dash`) if the site is served from a sub-path |

## The build-time-data rule

Every number or statement about results is read from files **at build time** (server components using `fs`,
see `lib/data.ts`):

- `$RESULTS_DIR/*.json` and `$RESULTS_DIR/discordant_subunits.csv`
- `../docs/prior-art.json`, `../docs/glossary.json`, `../demo/agent_session.md`, `../benchmarks/PREREGISTRATION.md`

Nothing in the JSX hard-codes a result or a claim of success. Pass/fail badges and "lower/higher error" labels
are computed from the files (`lib/results.ts`). If a file is missing or invalid the page shows a visible
"not available yet" notice and the build still succeeds. Every results page carries a provenance line
(source directory, files, `run_meta.json` code_commit, quick flag, runtime). Rebuild after the benchmark runs.

The site makes no network requests at runtime: no analytics, no external fonts, no chart library, and
Next.js telemetry is disabled in the npm scripts.

## Glossary terms

`docs/glossary.json` is the single source of truth. At build time the glossary is passed to a client component
(`components/GlossaryProvider.tsx`); term occurrences in prose (first per paragraph, including `aka` names)
become buttons that open a popover (desktop) or bottom sheet (mobile) with nested navigation, Back, Escape to
close, and a focus trap. Missing/invalid glossary renders "glossary not available yet".

## Checks

`scripts/check.cjs` uses an existing Playwright install (it never installs browsers) to screenshot each page at
375×812 and 1280×800 into `screenshots/`, assert no horizontal overflow, assert no external requests, and tap
glossary terms:

```bash
python3 -m http.server 4173 -d out &
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NODE_PATH=$(npm root -g) node scripts/check.cjs http://localhost:4173 screenshots
```

## Deploy

The output is a static site. Either:

- **Upload `dashboard/out/` as-is** to any static host (GitHub Pages, Netlify drop, S3, Cloudflare Pages with no
  build step). If it is served from a sub-path, rebuild with `NEXT_BASE_PATH=/that/path`.
- **Or deploy the `dashboard/` directory** to Vercel / Netlify / Cloudflare Pages with the **Next.js** framework
  preset (build command `npm run build`, output directory `out`). The repository root must be available to the
  build, because the build reads `../results`, `../docs`, `../demo` and `../benchmarks`.

Note: `npx vercel deploy dashboard/out --prebuilt` is **not** the right command; `--prebuilt` expects Vercel's
`.vercel/output` build format, not a plain static export.
