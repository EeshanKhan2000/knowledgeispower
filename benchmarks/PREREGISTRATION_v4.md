# Preregistration v4: low-data ("cold-start") regime, independent dataset

Committed **while the v3 confirmation was still running and before its result was seen**. So v4 cannot be
shaped by v3's outcome. The design comes only from Petrosius dev results
(`results/phase2/dev/dev_results_lown_fixed.json`, logged in `docs/EXPLORATION_LOG.md`).

## Hypothesis (narrower than phase 1, stated up front)
When few cells are measured, adding **curated complex membership (Complex Portal)** to a data-derived
neighbour graph improves imputation more than adding a degree-preserving shuffle of it. It also beats the
data graph alone and kNN.

Analogies: cold-start in recommender systems; Bayesian shrinkage. A fixed prior should matter most when
the data can't estimate neighbours well.

## Method (fixed; same code as Petrosius dev)
**E1+E4:** gated residual-on-kNN (`phase2.residual_on_knn(..., K=loo_knn(X), gate=1.0)`) run on the graph
**union(data-derived graph, Complex Portal)**.
- The data graph is `phase2.data_graph` with the same edge count as Complex Portal, built from each
  masked training matrix.
- The overlap threshold is min(30, max(5, n/2)).

## Data, subsamples and masks
- **Data:** Leduc 2022 (`leduc2022_pscope_proteins_norm2.h5ad`).
- **Subsamples:** 10 stratified cell subsamples per regime (equal numbers per cell type), with seeds
  **3000–3009**. The same seed drives the subsample and its mask.
- **Regimes:** **n = 30 cells (primary)** and n = 60 cells (secondary).
- **Masks:** in each subsample, the phase-1 generator (10% of observed entries of proteins detected in
  ≥ 50% of that subsample's cells), MCAR and MNAR.

## Comparators (primary: all must be beaten at n = 30)
1. **union(data graph, Complex Portal null):** the mean over null seeds 0–4.
2. **Data graph alone.**
3. **kNN:** the same leave-one-out kNN base, without a graph.

## Pass criterion (primary)
- **Where:** n = 30, in-complex stratum, **both** MCAR and MNAR.
- **Test:** the method must have lower RMSE than each comparator. "Lower" means the 95% paired bootstrap CI upper bound is < −1e-9 (1000 resamples of masked entries, pooled over the 10 subsamples, resample seed 17).
- **All 6 comparisons must pass.** If they do, the claim is reported as **confirmed in the low-data regime, on an
  independent dataset**, with effect sizes as a percentage. Otherwise it is **not confirmed**.

## Secondary (reported only)
- The same comparisons at n = 60.
- CORUM in place of Complex Portal.
- E1+E4 on Complex Portal alone, without the data graph.

## Outputs
`results/phase3/confirm_v4.json`, written by `benchmarks/confirm_v4.py`. Single use; it refuses to run on
uncommitted code.
