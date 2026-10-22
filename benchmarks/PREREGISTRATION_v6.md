# Preregistration v6: khan2023 holdout confirmation (Amendment 12)

Committed **before** khan2023 is evaluated. Until now khan2023 has been inspected for shape and missingness only.

- **Method:** `stack3_big`. This is a weighted average w_knn·kNN + w_lr·low-rank + w_t·reference projection. The weights
  are on the simplex grid with step 0.25, chosen per subsample on a 10% inner mask of *observed* entries.
- **Reference:** all 17 datasets from `transfer.extended_corpus()` (none excluded, since khan2023 is not among them) plus
  CCLE and ProteomeHD. Loadings are learned by masked ALS with rank 20, λ = 5, 15 iterations and ≥ 20 observations.
- **Data:** `data/datasets/khan2023_proteins_unimputed.h5ad` (421 MCF-10A cells, days 0, 3 and 9 of EMT; 4096 proteins).
- **Design:** 30-cell subsamples (10 per day), seeds 6000–6009. MCAR and MNAR masks come from `benchmarks/run.py::make_mask`
  on proteins observed in ≥ 50% of the subsample.
- **Primary comparators:** kNN, low-rank (`grmf`, λ_g = 0), the kNN + low-rank stack, and the mean of the two
  permuted-loading nulls.
- **Pass, per comparator and mask:** the 95% paired-bootstrap CI (1000 resamples, seed 17) of ΔRMSE is entirely < 0, and
  ΔRMSE is ≤ −1% of the comparator's RMSE.
- **H12 is confirmed** only if all four primary comparators pass under both masks (8/8).
- **Secondary:** `stack2_all` (the Amendment-10 reference), plus the weights chosen.
- **Disclosure:** this method did not pass the dev qualification rule (Amendment 11: 1/3 targets). The test is post-gate.
- **Single use:** `confirm_v6.py` refuses to run twice or with uncommitted code.
