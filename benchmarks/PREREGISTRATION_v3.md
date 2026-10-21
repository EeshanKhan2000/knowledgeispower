# Preregistration v3: independent-dataset confirmation (Leduc 2022)

Committed **before any evaluation on the Leduc 2022 dataset** (see `EXPLORATION.md` Amendment 2;
the only facts looked at so far are shape, missingness and label counts). The method is chosen from
**Petrosius evidence only**: it is the one phase-2 method whose curated version beat every
comparator on both held-out Petrosius masks (v2 secondary analysis, `docs/EXPLORATION_LOG.md`).
Phase 1 and v2 remain as reported.

## Primary method
**E6: Complex Portal partner residuals on a low-rank base** (`scp_graphfs_mcp.phase2`).
- **Base:** `grmf(X, None, lam_g=0, rank=10, lam=1.0, iters=400, lr=0.05, seed=0, full=True)`. This is the
  low-rank reconstruction of every entry.
- **Correction:** x̂ = base + β · (edge-weighted mean of the observed partners' residuals x − base, same cell),
  using the Complex Portal graph built over the dataset's proteins. β is one scalar, fitted by least
  squares on observed training entries. Only missing entries are filled.

These settings are identical to v2. Nothing is re-tuned on Leduc.

## Data and masks
- **Data:** `data/datasets/leduc2022_pscope_proteins_norm2.h5ad`, all 1543 cells (SHA-256 in `PROVENANCE.md`).
- **Masks:** the phase-1 generator (10% of observed entries of proteins detected in ≥ 50% of cells),
  MCAR and MNAR, **seeds 2000–2004**, run once.

## Comparators (all must be beaten)
1. **Low-rank without a prior:** the base alone, which is the strongest data-alone model on Petrosius.
2. **E6 on Complex Portal's degree-preserving nulls,** seeds 0–9, using the mean RMSE of the 10.
3. **E6 on a data-derived co-variation graph** with the same edge count as Complex Portal, built from each
   masked training matrix (`phase2.data_graph`).
4. **kNN:** `scp_prep` k = 10.

## Pass criterion (primary)
- **Where:** in the **in-complex** stratum, on **both** MCAR and MNAR.
- **Test:** E6 with Complex Portal must have lower RMSE than each of the 4 comparators. "Lower" means the 95% paired bootstrap CI of the difference has an upper bound < −1e-9 (1000 resamples, pooled over seeds, resample seed 17).
- **All 8 comparisons must pass.** If they do, we report the claim as **confirmed on an independent
  dataset, for this method**, together with the effect size. Otherwise it is **not confirmed**.

The CIs are optimistic (phase-1 Deviation 4). The effect size will be reported as a percentage of the
base RMSE, so a statistically clear but tiny gain is not oversold.

## Secondary (reported, never used to claim success)
- E6 with CORUM and with STRING.
- E3 (low-rank + Laplacian) with CORUM, Complex Portal and STRING.
- The not-in-complex stratum, where E6 should equal the base.

## Outputs
`results/phase3/confirm_v3.json`, written by `benchmarks/confirm_v3.py`. The script refuses to run twice or on
uncommitted code.
