# Independent verification

- **Date:** 2026-10-21
- **Branch / commit verified:** `claude/happy-hamilton-kdexid` @ `867e76e47cfb5d68fef57513a2866f84150035ab` (fresh clone; HEAD of the local checkout is the same commit)
- **Environment:** Python 3.13 venv, `pip install -e ".[dev]"` (scp-prep pulled from GitHub), Node 22.22.0 / npm 10.9.4, Playwright 1.56.1 + Chromium 1194.
- **Verifier stance:** looking for problems. Nothing in the repo was changed except this file.

## Summary

| # | Check | Result | One-line evidence |
|---|---|---|---|
| 1 | Citations (README, CITATION.cff, prior-art.json) | **PARTIAL** | All 13 README/CFF DOIs, 3 arXiv IDs, 32 prior-art DOIs re-fetched; titles, first authors, years and venues match. GIRAFI's "uses a STRING prior" could not be checked (bioRxiv full text returned 429 every try). NIFty author order differs between Crossref and bioRxiv. |
| 2 | Reproducibility | **PASS** | `pytest -q -m "not network"`: 18 passed, 27 xfailed. A full rerun (575 s) gives results identical to the committed JSON (max abs diff 0). `discordant_subunits.csv` is byte-identical. |
| 3 | README headline traceability | **PASS** (minor caveat) | `update_readme_headline.py` regenerates README.md byte-identically. Every number comes from results/. A few qualitative sentences are hard-coded, and one of them is imprecise. |
| 4 | Dashboard traceability | **PASS** (with a display bug) | `npm ci && npm run build` succeed and there are no hard-coded result literals in the dashboard source. 9 numbers traced to JSON. Float-noise rows show as significant "wins". |
| 5 | Slot tests derive from snapshots | **PARTIAL** | S1 tests derive their expected values from the snapshots. The S2 provenance assertion always passes, and S3 has the same weakness. |
| 6 | Contrib isolation | **PARTIAL** | `--include-contrib --out results` is refused (exit 1) and the default output is `results/contrib/`. A subdirectory of results/ is accepted, and `--quick`/`--normalise` may overwrite core `results/`. |
| 7 | Provenance | **PASS** | `fetch_data.sh` prints OK for all 7 files. Fresh downloads of CORUM, Complex Portal and HGNC match the SHA-256s, and the rebuilt STRING subset matches too. Every tracked data file has a row. |
| 8 | Preregistration integrity | **PASS** (one inaccurate sentence) | The prereg (15:44:57Z) predates the first results commit (16:01:22Z). Later edits only append Deviations. Deviation 1 misdescribes the diff. |
| 9 | Mobile + glossary | **PASS** | 375×812 on /, /mechanism/, /results/: 10 taps opened 10 sheets with content (9 distinct terms). scrollWidth = clientWidth = 375 everywhere and no page errors. |
| 10 | Honesty / consistency | **PARTIAL** | Numbers in submission/ and AGENTS.md match results/. The negative verdicts are reported plainly. Several sentences are stronger or less accurate than the data: "~1100" coverage, "curated graph structure", "Random beat every scored panel", "All entries were verified". |

---

## 1. Citations — PARTIAL

**README.md and CITATION.cff DOIs** (from `https://api.crossref.org/works/<DOI>`):

| DOI | Crossref title / first author / date / venue | Matches README/CFF? |
|---|---|---|
| 10.1016/j.cels.2017.08.013 | Widespread Post-transcriptional Attenuation of Genomic Copy-Number Variation in Cancer / Gonçalves +5 / 2017-10 / Cell Systems | yes |
| 10.64898/2026.05.18.726081 | Recovering biological structure in sparse single-cell proteomics with GIRAFI / Zhong +15 / 2026-05-21 / bioRxiv | yes (bibliographic) |
| 10.1016/j.mcpro.2025.100982 | Quantitative Label-Free Single-Cell Proteomics on the Orbitrap Astral MS / Petrosius +17 / 2025-06 / MCP 24(6) | yes |
| 10.1186/s12920-016-0228-z | Fuzzy-FishNET … / Goh (sole author) / 2016 / BMC Med Genomics 9(S3):67 | yes |
| 10.1093/bib/bbaf692 | Protrec2 … / Kong, Goh, Wong / 2025 / Brief Bioinform 26(6) | yes |
| 10.64898/2026.03.06.710179 | Classification with Missing Data - A NIFty Pipeline for Single-Cell [Proteomics] / Nitz +3 / 2026-03-09 / bioRxiv | yes |
| 10.1038/s41587-023-01905-6 | GEARS / Roohani +2 / online 2023-08-17, print 2024-06, Nat Biotechnol 42 | yes ("2024") |
| 10.1038/s41592-026-03142-6 | A comprehensive benchmark of sequence-based subcellular localization predictors… / Wefers +4 / 2026-07 / Nat Methods 23(7) | yes |
| 10.1371/journal.pcbi.1000641 | Associating Genes and Protein Complexes with Disease via Network Propagation / Vanunu +4 / 2010 | yes |
| 10.1093/nar/gkae1033 | CORUM in 2024: protein complexes as drug targets / Steinkamp +8 / print 2025-01 NAR 53 | yes (CFF year 2025 = print) |
| 10.1093/nar/gkae1085 | Complex portal 2025 … / Balu +15 / print 2025-01 NAR 53 | yes |
| 10.1093/nar/gkae1113 | The STRING database in 2025 … / Szklarczyk +14 / print 2025-01 NAR 53 | yes |
| 10.1101/2023.06.06.543943 | Evaluating the capabilities of the Astral mass analyzer for single-cell proteomics / Petrosius +14 / 2023-06-08 / bioRxiv | yes. The abstract mentions "a primary AML culture model", which is consistent with OCI-AML8227. |

**arXiv** (`export.arxiv.org/api/query?id_list=2604.20263,2509.23426,2507.08055`):
- AROMA: Wang, Ye, Liu, Ng, 2026-04-22, "Accepted to ACL 2026 as a Findings paper".
- ToolUniverse: Gao +10, 2025-09-27.
- MCPmed: Flotho +5, 2025-07-10.

All three match. The README claim that AROMA merges STRING and CORUM into one graph is confirmed by the arXiv HTML: "Gene-KG integrates STRING … and CORUM … into a gene-level association network".

**URLs:**
- `https://string-db.org/help/mcp/` returns 200 and the page is titled "STRING MCP Server".
- `git ls-remote https://github.com/PayneLab/nifty` returns HEAD `da3db09a…`, branch `main`, so the repo exists.
- `github.com/meringlab/string-mcp` also exists (ls-remote OK).

**docs/prior-art.json:** I ran a scripted check of all 35 entries: 32 with DOIs against Crossref, 3 via arXiv or URL. Titles, authors, years and venue/volume/issue/pages match for every DOI entry. The automatic flags were reviewed by hand:
- MCPmed has a "title mismatch", but this is only arXiv vs journal capitalisation and is acceptable.
- LamanTrip has a two-word surname, which the script misread as a mismatch. It is a false positive.
- **NIFty:** the json lists authors as Nitz, Echarry, McGee, Payne. This matches `api.biorxiv.org`, but Crossref lists Nitz, **McGee, Echarry**, Payne. The upstream sources disagree; this is not a fabrication.

Spot-checked claims (full text where reachable):
- **Wefers 2026:** confirmed from Europe PMC full text (PMC13345906). It says "ProtT5-MHA-PPI did not substansially outperform ProtT5-MHA by any average metric"; GraphSAGE was used, with BioPlex and STRING as the PPI data. The quote is accurate, including "[sic]".
- **Petrosius 2025:** confirmed from Europe PMC full text (PMC12209951): "as a proof of concept, we explore protein covariation… MCM helicase complex subunits and proteasome subunits".
- **Gonçalves 2017, Fuzzy-FishNET, Protrec2, NIFty:** confirmed from abstracts. Protrec2 is about complexes, Bayesian recovery of missing proteins, and bulk data. NIFty is top-scoring-pairs, needs no imputation, and is for SCP.
- **GIRAFI:** **not verified.** The abstract says only "prior-knowledge-informed protein neighborhoods". The claims "STRINGdb version 11.5" and "no shuffled-network control" need the full text. bioRxiv returned HTTP 429 or Cloudflare error 1015 on 4 attempts, and the Europe PMC preprint full text (PPR1235625) returned HTTP 500. The README states "It uses a STRING prior" as fact (README.md:69).
- **MAP-KG** carries an `unverified_note` ("CORUM inclusion unverified"), yet README.md:65 says "All entries were verified".

## 2. Reproducibility — PASS

```
pytest -q -m "not network"            -> 18 passed, 27 xfailed in 5.13s
python benchmarks/run.py --out <scratch>/rerun   -> done in 575s, exit 0
python3 -I cmp.py results <scratch>/rerun   (ignores run_meta runtime_seconds/code_commit, tol 1e-9)
  classification.json IDENTICAL max|d|=0
  coverage.json       IDENTICAL max|d|=0
  cross_context.json  IDENTICAL max|d|=0
  imputation.json     IDENTICAL max|d|=0
  panel.json          IDENTICAL max|d|=0
  stability.json      IDENTICAL max|d|=0
  verdicts.json       IDENTICAL max|d|=0
  run_meta.json       2 DIFFS: /normalise, /preregistered only in rerun
cmp results/discordant_subunits.csv rerun/...  -> byte-identical (sha256 d60f1a5f…)
```

The two run_meta keys are new because `run.py` was changed after the committed run (f26b423, 4cd1ee8). That is expected and does not affect the results. The committed run was made at code `7626455`; I reran at HEAD `867e76e`, so the later run.py edits did not change any number. 27 of the tests are strict-xfail slot acceptance tests, so the 18 passes are the real core tests.

## 3. README traceability — PASS (minor caveat)

- I copied README.md, results/ and the script into a scratch tree and ran `python scripts/update_readme_headline.py`. `cmp` showed the output is **BYTE-IDENTICAL** to README.md.
- Every numeric value in the block is formatted from imputation/panel/stability/classification/verdicts/coverage/run_meta JSON or from discordant_subunits.csv (script lines 58–110).
- Hard-coded *qualitative* sentences in `scripts/update_readme_headline.py` are not recomputed. I checked them against the data:
  - l.86 "Every prior beats its own shuffled null": true. In-complex Δ vs own null is negative with the CI excluding 0 for all 4 priors × 2 masks.
  - l.95 "Random beat every scored panel at k=25 and k=50": **imprecise.** At k=50 (all stratum), `string__null_mean` = 0.421 > `random_mean` = 0.419 (panel.json `"50"."all"`). Random beats every *real-prior* and HVP panel, but not every scored panel.
  - l.99–100 "Complex Portal is best of the four … STRING-combined beats STRING-experimental": true on both masks (verdicts.json test4).
  - l.78 "curated priors fall back to kNN, so they are identical": true (not_in_complex RMSE identical to kNN, 0.79581 MCAR, 0.84983 MNAR).
  - l.33 "per-cell scale does not explain kNN's advantage" is an interpretation. The exploratory numbers support "did not remove it".

## 4. Dashboard traceability — PASS (display bug)

- `npm ci && npm run build` exits 0. The build exports 8 routes.
- I grepped `dashboard/app`, `components` and `lib` for decimal literals and found only SVG opacity values (0.15, 0.55). The other integers are layout values, the schematic bar heights in `app/mechanism/page.tsx:91-125` (illustrative, not results), and the design constant "k = 25, 50, 100" (`app/pipeline/page.tsx:124`).
- All results come through `lib/data.ts` (`fs.readFileSync` of `../results/*` at build time).

Nine numbers from `dashboard/out/results/index.html`, traced to JSON:

| Shown | Source | Value |
|---|---|---|
| Eligible proteins 1,672 | imputation.json `eligible_proteins` | 1672 |
| CORUM shuffled nulls, in-complex MCAR range 0.836 – 0.850 | imputation.json MCAR rows `corum__null*`/in_complex | 0.83602 – 0.84975 |
| Complex Portal vs kNN in-complex share by prior 0.53, entries 93,798 | comparisons `frac_entries_imputed_by_prior`, `n_entries` | 0.52597, 93798 |
| CORUM panel chart, in-complex HVP k=25 0.219 | panel.json `25.in_complex.hvp` | 0.21929 |
| random k=50 0.443 | `50.in_complex.random_mean` | 0.44299 |
| CORUM nulls k=50 0.402 | `50.in_complex.corum__null_mean` | 0.40189 |
| CORUM k=100 0.299 | `100.in_complex.corum` | 0.29855 |
| Stability Complex Portal 0.761 | stability.json `complexportal` | 0.76141 |
| Classification CORUM null range 0.747 – 0.804 | classification.json `corum__null_range` | 0.74708 – 0.80433 |
| Discordant: 596 rows; NUDC r −0.102, z 11.3 | discordant_subunits.csv | 596; −0.1018; 11.2973 |

**Bug:** the results page labels "CORUM/Complex Portal vs own shuffled nulls, not in a complex" as "✓ prior lower error (CI excludes 0)" with ΔRMSE +0.000.
- The underlying JSON has `delta_rmse` = 1.1e-16, `ci95` = [−2.0e-14, −1.1e-14] and `significant_improvement: true`. This is floating-point noise: the predictions are identical, because both fall back to kNN.
- As a result, 4 of the "12 with lower error" MCAR comparisons are not real wins, and the same applies to MNAR.
- Root cause: `benchmarks/run.py:178` (`significant_improvement = ci95[1] < 0`, no tolerance), repeated in `dashboard/lib/results.ts:31`.
- Verdicts are unaffected, because they use only the in_complex stratum.

UI nit: the Cross-context section renders raw `JSON.stringify` blobs (`dashboard/app/results/page.tsx:90`, section at :425).

## 5. Slot tests — PARTIAL

**`tests/test_variant_bridge.py`: OK.**
- Complex IDs come from `complexes_for_accession` / `uniprot_for_symbol` at test time (l.40–44, 73, 81, 100, 129, 138, 171).
- `NO_COMPLEX_CANDIDATES` is asserted against the snapshot in-test (l.88–89).
- The MB1 ambiguity is checked in-test (l.115–116).
- Hard-coded assumptions that are *not* checked against the snapshot in-test:
  - l.74 `"proteasome"` and l.82 `"rna polymerase ii"` name substrings;
  - l.155 `"P99999"` (a real accession, CYCS) is assumed not to be a PSMB5 partner;
  - l.120 assumes `resolve_symbol` returns a sorted list.
- I verified all of these hold in the current snapshot: the PSMB5 complexes are named "...proteasome...", POLR2A has "RNA polymerase II core complex", P99999 is not a PSMB5 partner, and `resolve_symbol('MB1')` = (['CD79A','PSMB5'], 'alias'). They would fail confusingly rather than silently if the snapshot changed.

**`tests/contrib/test_s2_dataset.py:21`: vacuous assertion.** `assert name in prov or a.uns.get("source_sha256", "") in prov`. When `source_sha256` is missing, `"" in prov` is always True, so the provenance requirement is never enforced.

**`tests/contrib/test_s3_prior.py:41`: same weakness.** `g.graph["provenance"]["sha256"] in prov` passes if sha256 is `""`.

Neither contrib test hard-codes IDs. Both open `data/PROVENANCE.md` with a cwd-relative path.

## 6. Contrib isolation — PARTIAL

```
python benchmarks/run.py --include-contrib --quick --out <scratch>/c   -> exit 0 (1m58s); git status --short: clean
python benchmarks/run.py --include-contrib --out results               -> "refusing: --include-contrib may not write to core results/", exit 1
python benchmarks/run.py --include-contrib --out ./results/../results/ -> refused
timeout 10 python benchmarks/run.py --include-contrib                  -> creates results/contrib/ (default confirmed; benchmarks/run.py:440)
timeout 15 python benchmarks/run.py --include-contrib --quick --out results/sneaky -> NOT refused (created results/sneaky)
timeout 15 python benchmarks/run.py --quick --out results              -> NOT refused (would overwrite core results with quick numbers)
```

The guard (`benchmarks/run.py:442-444`) only tests equality with `results/`. Two holes remain:
- `--include-contrib` can write into any subdirectory of core `results/` other than `results/contrib`.
- `--quick` and `--normalise median` can be pointed at `results/` and would silently replace the preregistered outputs. `run_meta.preregistered` would record this, but nothing stops it.

Also note that `load_contrib()` currently registers **no** contrib priors, methods or datasets, so the contrib path has only been exercised with zero contrib entries.

## 7. Provenance — PASS

```
SSL_CERT_FILE=/root/.ccr/ca-bundle.crt ./scripts/fetch_data.sh
  OK data/raw/corum_humanComplexes.txt
  OK data/raw/complexportal_9606.tsv
  OK data/raw/hgnc_complete_set.txt
  OK data/cache/string/9606.protein.links.detailed.v12.5.txt.gz
  OK data/cache/string/9606.protein.aliases.v12.5.txt.gz
  OK data/datasets/petrosius2023_aml_sc.h5ad
  OK data/derived/string_v12.5_9606_uniprot.tsv.gz
```

The script skips any file that already exists (`[ -s "$dest" ] && … return`). For committed files, "OK" therefore only proves the file matches its own recorded hash, not that it can be re-downloaded. To close that gap I downloaded CORUM, Complex Portal and HGNC fresh into a scratch dir: all three SHA-256s match PROVENANCE.md. I also reran `scripts/build_string_subset.py`, which reproduced `data/derived/…tsv.gz` with sha256 `a933a71d…`, identical to the recorded hash.

Tracked data files (`git ls-files data`) are: 3 raw, 1 derived, 1 dataset. Each has a PROVENANCE row. The dataset h5ad was built in a different repo (`xX-its-amit-Xx/scp-benchmark@252372a`), so it cannot be rebuilt from this repo alone. This is disclosed.

## 8. Preregistration integrity — PASS (one inaccurate sentence)

```
git log --format='%H %cI' -- benchmarks/PREREGISTRATION.md
  9a5b70f 2026-10-21T16:13:29Z  (append to Deviations)
  f26b423 2026-10-21T16:02:32Z  (append Deviations 1-2)
  445c19a 2026-10-21T15:44:57Z  (initial, 90 lines)
git log --format='%H %cI' -- results/
  9a5b70f 2026-10-21T16:13:29Z
  21ae44e 2026-10-21T16:01:22Z  (first results)
```

- The prereg commit precedes the first results commit by 16 min. It also precedes the commit that added `benchmarks/run.py` (f0fb4b6, 15:51), which is consistent with "committed before any benchmark code ran". Commit timestamps are self-reported and do not rule out quick local runs between 15:51 and 16:01.
- Both later diffs touch only the `## Deviations` section. The Methods, Tests and Pass criteria sections are unchanged.
- **Inaccuracy:** Deviation 1 (`benchmarks/PREREGISTRATION.md:92`) says the only change between f0fb4b6 and 7626455 touching `benchmarks src/scp_graphfs_mcp data` was one PROVENANCE line. Running the cited `git diff --stat f0fb4b6 7626455 -- benchmarks src/scp_graphfs_mcp data` also shows `src/scp_graphfs_mcp/tools.py | 172 +++`. `tools.py` is the MCP tool layer and `run.py` does not import it, so the conclusion ("no effect on the analysis") still holds, but the sentence is wrong.

## 9. Mobile + glossary — PASS

I served `dashboard/out` with `python3 -m http.server 8765` and ran Node Playwright with Chromium at 375×812 (isMobile, hasTouch) and a seeded random choice of `[data-term]` buttons. Script: scratchpad `pw/check.cjs`.

```
/            scrollWidth=375 clientWidth=375, scrollTo(500,0)->scrollX=0; 15 terms
  RMSE -> sheet "RMSE" (633 chars) · PPI -> "PPI" (1216) · "protein machines" -> "protein complex" (1442)
/mechanism/  scrollWidth=375; 15 terms
  EBI Complex Portal -> "Complex Portal" (1127) · proteasome (1115) · degree-preserving shuffle (1002)
/results/    scrollWidth=375; 12 terms
  prior (894) · bootstrap (964) · RMSE (633) · prior [different instance] (894)
pageerrors=[]
```

- Every tap opened a bottom sheet (`[data-glossary-sheet]`, 375×650 at y=162) with heading and body. I inspected one screenshot and it renders cleanly.
- No horizontal overflow: no unclipped element extends past 375 px, before or after any tap.
- 10 taps covered 9 distinct terms ("prior" was picked twice on /results/).

## 10. Honesty — PARTIAL

**Consistent:**
- submission/summary_150w.md (0.730 / 0.807 / 0.687, 215 cells, 40.7%) matches results/.
- AGENTS.md:116 matches results/.
- video_script and miro_pitch report the failed headline plainly.
- The README states that test 1, 2 and 4 failed and that test 3 passed "by a negligible margin" (CP 0.7614 vs null 0.7599; the null range 0.753–0.767 contains the prior).
- summary_150w is 128 words of body text, within the ≤150 limit.

**Overstatements and inaccuracies:**
1. README.md:101 "Only ~1100 of 2813 proteins here have any curated-complex partner." From the data, CORUM gives 1147 proteins with edges, Complex Portal 847, and their **union is 1317** (computed with `build_prior`). "~1100" understates the curated coverage by ~16%.
2. README.md:32 "Every prior beats its own shuffled null, so the **curated** graph structure carries real signal."
   - STRING (not curated) beats its null by more: −0.134 vs −0.076 for Complex Portal, MCAR in-complex.
   - The README's own caveat shows null partners already reach median r = 0.63.
   - The supported statement is "each graph's specific wiring adds signal beyond degree". It is not curated-specific.
3. submission/miro_pitch.md:3 "Curated protein complexes beat shuffled graphs but not kNN". This is true, but it implies a curated-specific advantage. STRING graphs beat their shuffles by more, and CORUM loses to STRING-combined on in-complex RMSE (0.771 vs 0.761 MCAR).
4. README.md:36 "Random beat every scored panel at k=25 and k=50": at k=50 the STRING-combined null mean (0.421) beats random (0.419).
5. README.md:65 "All entries were verified" while `docs/prior-art.json` MAP-KG has an unverified_note. The README.md:69 GIRAFI STRING claim could not be independently re-verified (see §1).
6. submission/video_script.md:5–6 "a large share of the values in each cell are missing, and mostly because they're low". This is not tested anywhere in results/; the benchmark's MNAR mask is an assumption. Soften it, or cite a source.
7. README.md:114 says Eeshan Khan is "listed as a contributor only if merged" while listing him in the Contributors section; CONTRIBUTORS.md says the same. This is a minor self-contradiction.

**Methodological caveats** (preregistration-compliant, but worth stating):
- The paired bootstrap resamples masked entries i.i.d. and pools 5 seeds whose masks overlap. It ignores clustering by cell and protein, so the CIs are optimistic. The large kNN gap is very unlikely to flip; small margins would need cell-level resampling.
- In the panel test, the kNN imputation of features and targets is done on all cells before the CV split (`test_panel`), which leaks a little information across folds. It applies to every method equally.

---

## Issues to fix (most severe first)

1. **Spurious "significant improvement" from float noise.**
   - Where: `benchmarks/run.py:178` sets `significant_improvement = c["ci95"][1] < 0`. In results/imputation.json, curated priors vs own null in not_in_complex (identical predictions) get `significant_improvement: true` with CI ≈ [−2e-14, −1e-14]. `dashboard/lib/results.ts:31` turns these into ✓ wins, so the results page counts 4 fake wins across the two masks ("12 with lower error").
   - Fix: require `ci95[1] < -1e-9` (or compare against a tolerance) in run.py, and treat |Δ| < 1e-9 as "no difference" in results.ts. Then regenerate results/. This changes no verdict, but it changes JSON flags, so log it as a Deviation.
2. **Output-path guard has holes.**
   - Where: `benchmarks/run.py:442-444` refuses only an exact `results/`.
   - What gets through: `--include-contrib --out results/anything` is accepted, and `--quick --out results` or `--normalise median --out results` silently overwrite the preregistered core results.
   - Fix: refuse any `out_dir` inside `results/` unless (contrib and under `results/contrib`) or (normalise and under `results/exploratory`). Refuse `--quick` targeting `results/`.
3. **Vacuous provenance assertions in slot contract tests.**
   - Where: `tests/contrib/test_s2_dataset.py:21` (`"" in prov` is always True) and `tests/contrib/test_s3_prior.py:41` (passes when sha256 is `""`).
   - Fix: `sha = a.uns.get("source_sha256"); assert sha and re.fullmatch(r"[0-9a-f]{64}", sha) and sha in prov`. Do the same for S3. Open PROVENANCE via `Path(__file__).parents[2]/"data/PROVENANCE.md"`.
4. **Coverage number wrong.**
   - Where: `README.md:101` "~1100 of 2813 proteins … have any curated-complex partner". The union of CORUM and Complex Portal is 1317 (CORUM alone 1147).
   - Fix: generate this line from `coverage.json` and add a `union_curated_with_edges` field in run.py's coverage block, or write "1317 (CORUM 1147, Complex Portal 847)".
5. **Overreaching interpretation sentence.**
   - Where: `README.md:32` (hard-coded at `scripts/update_readme_headline.py:86`) "so the curated graph structure carries real signal".
   - Fix: "so each graph's specific wiring carries signal beyond its degree distribution; STRING gains more over its null than the curated priors do". Mirror the change in `submission/miro_pitch.md:3`.
6. **Imprecise hard-coded claim.**
   - Where: `README.md:36` (`scripts/update_readme_headline.py:95`) "Random beat every scored panel at k=25 and k=50". At k=50, `string__null_mean` 0.421 > random 0.419.
   - Fix: compute the sentence from panel.json, or say "Random beat HVP and every real-prior panel at k=25 and k=50".
7. **Deviation 1 misstates the diff.**
   - Where: `benchmarks/PREREGISTRATION.md:92` says the only change was one PROVENANCE line. The cited diff also includes `src/scp_graphfs_mcp/tools.py` (+172 lines; MCP tools, not imported by run.py).
   - Fix: append a correction to Deviations (do not edit the original line), e.g. "Correction: the diff also adds MCP tool code in tools.py, which run.py does not import".
8. **"All entries were verified" is not quite true.**
   - Where: `README.md:65`. MAP-KG has `unverified_note`, and GIRAFI's STRING-prior detail depends on a bioRxiv full text that is currently rate-limited.
   - Fix: "All 35 entries' bibliographic metadata were verified; one component claim (MAP-KG uses CORUM) is unverified". Keep the hedged GIRAFI wording ("per its full text, a STRING v11.5 prior") at README.md:69.
9. **Untested premise in the video script.**
   - Where: `submission/video_script.md:5-6` "missing, and mostly because they're low".
   - Fix: soften to "often because they're low-abundance", or cite a source.
10. **fetch_data.sh does not re-verify committed snapshots against upstream.**
    - Where: `scripts/fetch_data.sh:18` skips existing files, so "OK" for data/raw only re-hashes the committed copy.
    - Fix: add a `--refetch` flag that downloads into a temp dir and compares, or reword the header comment (line 2) to "verify SHA-256 of local files; re-download missing ones".
11. **Dashboard cross-context section dumps raw JSON.**
    - Where: `dashboard/app/results/page.tsx:90` (used by the section at :425).
    - Fix: render cross_context.json with the same table component used for panel/stability.
12. **Optimistic CIs (methodological; disclose).**
    - Where: `benchmarks/run.py:105-121` resamples entries i.i.d. and pools overlapping seed masks.
    - Fix: add a README limitation, and optionally an exploratory cell-level block bootstrap.
13. **Minor test fragility.**
    - Where: `tests/test_variant_bridge.py:74,82` hard-code name substrings; `:155` assumes P99999 is not a PSMB5 partner; `:120` assumes `resolve_symbol` returns a sorted list.
    - Fix: assert those preconditions from the snapshot in-test, as already done for `NO_COMPLEX_CANDIDATES`.
14. **Contributor wording contradiction.**
    - Where: `README.md:114` "listed as a contributor only if merged" while he is listed.
    - Fix: "S1 in progress (Eeshan Khan); credited on merge".
15. **NIFty author order.**
    - Where: `docs/prior-art.json` NIFty `authors` follows bioRxiv (Nitz, Echarry, McGee, Payne), while Crossref has Nitz, McGee, Echarry, Payne.
    - Fix: no change needed beyond a note in `verified_via` that the sources disagree.

---

## Fixes applied after verification (2026-10-21)

| # | Issue | Fix |
|---|---|---|
| 1 | Rounding noise counted as significant wins | `benchmarks/run.py`: `SIG_TOL = 1e-9`; dashboard `lib/results.ts` uses the same tolerance. Results regenerated; logged as Deviation 3 in `PREREGISTRATION.md`. No verdict changed. |
| 2 | Output-path guard holes | `run.py` now refuses quick runs under `results/`, contrib runs outside `results/contrib/`, exploratory runs outside `results/exploratory/`, and core runs into a subdirectory. All four cases tested. |
| 3 | Provenance assertions that could not fail | S2 and S3 contract tests require a 64-hex SHA-256 that appears in `PROVENANCE.md`. |
| 4 | Coverage number | README now says 1317 of 2813 (CORUM 1147, Complex Portal 847), recomputed. |
| 5 | Overreach ("curated structure carries signal") | README headline, Miro card, video script and summary now say that STRING beats its null too, so no curation-specific effect is shown. |
| 6 | Imprecise panel claim | The sentence now compares random panels with real priors and HVP only, and the script checks this against `panel.json`. |
| 7 | Deviation 1 misstated the diff | Correction added under Deviation 1. |
| 8 | "All entries were verified" | Reworded: DOI metadata was verified; some full-text claims are not (`unverified_note`); the GIRAFI detail could not be re-checked. |
| 9 | Untested premise in video script | Reworded as an assumption we didn't test. |
| 10 | `fetch_data.sh` only re-hashed local copies | Added `--refetch`, which re-downloads and compares; PROVENANCE wording fixed. |
| 11 | Raw JSON on dashboard | Nested objects are no longer printed as JSON; they render as tables. |
| 12 | Optimistic CIs | Stated in README limitations and as Deviation 4. |
| 13 | Fragile S1 test premises | Premises are now asserted against the snapshot in-test. Assertions were added only, never weakened. |
| 14 | Contributor wording | S1 credit line now reads "in progress; credited here once merged". |
| 15 | NIFty author order | Note added to `docs/prior-art.json`. |
