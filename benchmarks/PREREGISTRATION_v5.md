# Preregistration v5: curated vs. data-derived partners, third dataset, with a minimum effect size

Committed before any evaluation on the SCoPE2 dataset (`EXPLORATION.md` Amendment 3).
- **Motivation:** across Petrosius (dev; v2 secondary) and Leduc (v3, v4 secondary), using **curated
  Complex Portal partners** gave lower imputation error than using **partners estimated from the data**, within the same
  model. v4 showed 3–5% at 30–60 cells.
- **Lesson from v3:** v3 lacked a smallest effect size of interest (SESOI), so v5 sets one.

## Claim under test (narrow, stated before the run)
In the low-data regime, curated complex membership is a better source of *which partner proteins inform a missing
value* than co-variation estimated from the same data, and better than a degree-preserving shuffle of itself.
**This is not a claim that the method beats kNN.** kNN is reported as a secondary row, and it may win.

## Method (fixed; identical code to v4)
**E1+E4:** gated residual-on-kNN, `phase2.residual_on_knn(Xm, G, names, K=phase2.loo_knn(Xm), gate=1.0)`.
- **Curated arm:** G = the **Complex Portal** graph.
- **Data arm:** G = `phase2.data_graph(Xm, names, n_edges = Complex Portal edge count)`, built from the masked
  training matrix of each subsample.
- **Null arm:** G = Complex Portal degree-preserving nulls, seeds 0–4, using the mean RMSE.

## Data, subsamples and masks
- **Data:** SCoPE2 (`specht2021_scope2_proteins_from_peptides.h5ad`).
- **Subsamples:** stratified, equal numbers of Macrophage and Monocyte cells, subsample seeds **4000–4009**.
  The same seed drives the mask.
- **Regimes:** **n = 30 (primary)** and n = 60 (secondary).
- **Masks:** the phase-1 generator within each subsample (10% of observed entries of proteins detected in ≥ 50% of
  its cells), MCAR and MNAR.

## Pass criterion (primary; all 4 must hold)
- **Where:** n = 30, in-complex stratum.
- **Comparisons:** for each mask (MCAR, MNAR) and each comparator (data arm; mean of the null arms):
  - the 95% paired bootstrap CI upper bound of ΔRMSE (curated − comparator) is < 0 (1000 resamples pooled over the 10 subsamples, seed 17), **and**
  - the point estimate is ≤ **−1% of the comparator's RMSE** (SESOI).
- **If all 4 hold:** report "confirmed on a third dataset, as scoped above". Otherwise, "not confirmed".

## Secondary (reported only)
- The n = 60 regime.
- CORUM in place of Complex Portal.
- Both arms vs. kNN.

## Output
`results/phase3/confirm_v5.json` from `benchmarks/confirm_v5.py`. Single use; it refuses to run on uncommitted code.
