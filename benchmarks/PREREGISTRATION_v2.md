# Preregistration v2: confirmation of the phase-2 method

Committed **before** the confirmation masks (seeds 1000–1004) were used for anything. The method was
selected on dev masks by the rule fixed in `benchmarks/EXPLORATION.md`; see `docs/EXPLORATION_LOG.md`.
The phase-1 result (`PREREGISTRATION.md`, `results/`) is unchanged and remains the primary record.

## Primary method (selected by the fixed rule)
**E3: graph-regularised low-rank completion with the CORUM prior** (`scp_graphfs_mcp.phase2.grmf`).
- **Model:** X is z-scored per protein using observed values. X ≈ U Vᵀ on observed entries, with rank 10.
- **Penalty:** λ(|U|² + |V|²) with λ = 1.0, plus λ_g · tr(Vᵀ L V) with λ_g = 1.0, where L is the Laplacian
  of the weighted CORUM graph.
- **Optimiser:** Adam, lr 0.05, 400 iterations, init seed 0. Only missing entries are filled.

## Data and masks
- **Data:** all 215 cells of the phase-1 dataset.
- **Masks:** the phase-1 generator (10% of observed entries of proteins detected in ≥ 50% of cells),
  MCAR and MNAR, **seeds 1000, 1001, 1002, 1003, 1004**, run once.

## Comparators (all must be beaten)
1. **kNN:** `scp_prep` k = 10.
2. **The same model without a prior:** λ_g = 0. This is the most direct "data alone" control.
3. **The same model on CORUM's degree-preserving nulls,** seeds 0–9 with λ_g = 1, using the mean RMSE of the 10.
4. **The same model on a data-derived co-variation graph** with the same edge count as CORUM, built from
   each masked training matrix (`phase2.data_graph`), λ_g = 1.

## Pass criterion (primary)
In the **in-complex** stratum, on **both** MCAR and MNAR, the primary method's RMSE is lower than each
of the 4 comparators. "Lower" means the 95% paired bootstrap CI of the RMSE difference has an upper
bound < −1e-9 (1000 resamples of masked entries, pooled over the 5 seeds, resample seed 17).
**All 8 comparisons must pass.** Otherwise the claim is **not confirmed**.

Known limitation: the CIs are optimistic (entries are not independent; see phase-1 Deviation 4).

## Secondary analyses (reported, never used to claim success)
On the same confirmation masks:
- **E6** (Complex Portal residuals on the λ_g = 0 low-rank base) vs. low-rank, the Complex Portal nulls (0–9) and the data graph.
- **E1+E4** (gated residual-on-kNN, Complex Portal) vs. kNN, nulls, the data graph and low-rank.
- **E3 with Complex Portal, STRING and STRING-experimental.**

All rows are reported, including losses.

## Outputs
`results/phase2/confirm/confirm_v2.json`, written by `benchmarks/confirm_v2.py`, which refuses to run
twice (it aborts if the output exists).
