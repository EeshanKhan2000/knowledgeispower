# S2: second dataset loader + cross-context test

**Goal:** add a second public single-cell proteomics dataset with **real, unimputed missingness**
so the benchmark can test transfer across datasets.

- **Suggested candidate:** Leduc et al. 2022 (nPOP / pSCoPE; melanoma + monocytes), from the
  `scpdata` ExperimentHub object `leduc2022_pSCoPE.Rda` (269 MB). Its `proteins_processed` assay is
  **imputed**, so it can't be used. You need an unimputed protein assay, or to aggregate peptides
  yourself.
- **Watch out:** melanoma vs. monocyte classification will likely hit a ceiling.
- **Where:** `contrib/s2_dataset/`. Register with `register_dataset("<name>", load, "...")`.
- `load()` returns AnnData that passes `registry.validate_dataset`, and has:
  - ≥ 500 proteins;
  - missing fraction ≥ 0.2;
  - an `obs['cell_type']` column.
- **Provenance:** ask Amit to add a row to `data/PROVENANCE.md` (URL, release, date, SHA-256).
  Don't commit files > 50 MB; download on first use into `data/cache/`.
- **No new dependencies.** If the source is an `.Rda` file, propose the reader first (R isn't
  assumed).
- **Contract:** `tests/contrib/test_s2_dataset.py` (xfail until a contrib dataset is registered).
- **Time box:** 3 h.
