# Contribution slots

Each slot is pre-scoped and off the critical path. Before anyone starts, Amit writes (or approves)
its acceptance tests. Claim one by commenting on its issue or asking Amit. Rules:
`CONTRIBUTING.md`. Agent instructions: `AGENTS.md`.

| Slot | Task | Good for | Off critical path because | Owner | Time box / checkpoint | Spec · tests |
|---|---|---|---|---|---|---|
| **S1** | Variant → complex bridge | Genomics, backend | Optional demo story | **Eeshan Khan** (@EeshanKhan2000) | Oct 21, 14:00 ET: **missed, no commits**. Unmerged; Amit may reopen | `docs/specs/variant_bridge.md` · `tests/test_variant_bridge.py` |
| S2 | ~~Second dataset~~ **Fourth dataset** (Leduc 2022 and SCoPE2 are done) + cross-context test | Data engineering | Stretch test only | *open* | 3 h | `docs/specs/S2_dataset.md` · `tests/contrib/test_s2_dataset.py` |
| S3 | Extra prior source. Candidates to *verify first*: hu.MAP, BioPlex-derived complexes, EMAPA/Cell Ontology | Bio/KG people | Goes to `results/contrib/` | *open* | 3 h | `docs/specs/S3_prior.md` · `tests/contrib/test_s3_prior.py` |
| S4 | NIFty baseline wrapper (only if its code is public) | ML people | Extra baseline row | *open* | 3 h | `docs/specs/S4_nifty.md` · `tests/contrib/test_s4_nifty.py` |
| S5 | MCP client recipes: Claude Desktop, Claude Code, one non-Claude agent framework, each with a working transcript | Agent/devtools people | Docs only | *open* | 2 h | `docs/specs/S5_recipes.md` |
| S6 | Glossary + dashboard explainer entries | Science communicators | Content in `docs/glossary.json` only | *open* | 2 h | `docs/specs/S6_glossary.md` · `tests/test_glossary.py` |
| S7 | Test hardening: edge cases, CI, type hints | Anyone careful | Can only make things safer | *open* | 2 h | `docs/specs/S7_hardening.md` |
| A | Hard-filter selection arm | Collaborator A | Extra benchmark arm | **Collaborator A** | TBD by Amit | `contrib/hard_filter/README.md` · `tests/test_hard_filter.py` |

## What today's findings change for each track (updated 2026-10-21 15:40 ET)

Source: README §2b, `docs/EXPLORATION_LOG.md`, and issue #1. **Rules for everyone:**
- **Used datasets are dev-only.** Petrosius 2023, Leduc 2022 and SCoPE2 have all been used for confirmations. New ideas may be *developed* on them, but a new *claim* needs a new, untouched dataset plus a committed preregistration with a **minimum effect size** (v3 showed why).
- **Strong data-only baselines are mandatory:** kNN, low-rank completion (`phase2.grmf(..., lam_g=0)`), a data-derived graph with matched edge count (`phase2.data_graph`) and degree-preserving nulls. Phase 1 compared against kNN only, and that turned out to be too weak a bar.

| Track | What we learned | What changes for you |
|---|---|---|
| **S1** variant bridge | (no new findings; checkpoint missed) | Unmerged. If reopened, the contract (`tests/test_variant_bridge.py`) is unchanged; pull the latest core first |
| **A** hard filter | HVP picks contaminants: 8 keratins in a 25-protein panel. Random panels beat HVP and propagation panels. Greedy coverage over curated complexes ≈ random, and beats its null by ~0.1 R² | Apply the W1 filter (`phase2.keratin_mask`) before ranking. Compare against **random** and **coverage** panels, not just HVP. Evaluate on dev CV seeds 100–102 (`benchmarks/explore_panel.py`) |
| **S2** datasets | Leduc and SCoPE2 are now loaders (`load_leduc2022`, `load_specht2021`). `.Rda` files can be read without R (`scripts/rda_*`). The scpdata `proteins` assays are often **imputed**; rebuild from unimputed peptides | Target a **fourth**, untouched dataset (e.g. plexDIA/Derks 2023, or another scpdata set), with ≥ 500 proteins and real missingness. It becomes the next held-out confirmation set |
| **All tracks** (17:30 ET) | Pooling co-variation from 5 external datasets and hu.MAP 3.0 did **not** help (dev, leave-one-dataset-out). On Leduc and SCoPE2, partner corrections are ≈ 0 after kNN or low-rank | "More data" in the form of external co-variation is not the missing inductive bias. Proposals now need a *different* mechanism or task (see Proposals below) |
| **All tracks** (00:00 ET, Oct 22) | **Knowledge as protein features** (GO, HPA, UniProt, PaxDb, spectral STRING/CP) beats *shuffled* features in every 30-cell test, so the knowledge is real. But it never beats kNN at 30 cells, and ensembling with kNN only helps through generic model averaging | Any new prior idea must beat **kNN, low-rank, and an ensemble with a shuffled-feature null**. Pharos, Monarch and INDRA remain untested (second tier), so they are open for anyone to try under the same rules |
| **S3** extra prior | **Complex Portal consistently beats CORUM** as a partner source (CORUM was worse than data-derived partners on SCoPE2). Curated partners beat data-derived ones by 3–5% on Leduc and ~1% on SCoPE2 | **hu.MAP 3.0 predicted complexes are now the top candidate.** Does a larger, predicted complex set beat curated Complex Portal? Use the matched-edge data graph and nulls as baselines; results go to `results/contrib/` |
| **S4** NIFty | NIFty already benchmarks on a Petrosius dataset (prior-art log) | Use it as a panel-selection baseline next to random and coverage panels |
| **S5** recipes | Six core MCP tools are live; contrib tools mount with `--enable-contrib` | No change |
| **S6** glossary | New concepts: preregistration, SESOI, forking paths, low-rank completion, residual stacking, cold-start | Add these terms to `docs/glossary.json` |
| **S7** hardening | The data-graph overlap bug (impossible ≥ 30 threshold at n < 30) was found and fixed; the significance tolerance was fixed | Add edge-case tests for small n and identical predictions in `tests/contrib/` |

Ideas outside the thesis (multi-omics, GNN embeddings, general KG) are logged below as proposals,
not code.

## Proposals (not scheduled)
- **Change the task, not the prior:** use stoichiometry where it constrains *observed* values (denoising, or detecting
  outlier subunits and orphan-subunit degradation) rather than imputing missing values that kNN already captures.
- **Peptide-level priors:** complexes constrain protein ratios. Imputing at peptide level, then aggregating, may expose more signal than protein-level kNN.
- **Bulk co-fractionation (CF-MS) profiles** as external evidence. They are richer than single-cell co-variation, but need a new data source.
- **Any new claim:** khan2023 is still an untouched holdout. Preregister with a SESOI before touching it.
