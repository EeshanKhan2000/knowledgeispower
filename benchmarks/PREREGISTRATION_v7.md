# Preregistration v7: brunner2022 holdout (Amendment 14, H14)

Committed **before** brunner2022 is evaluated. Until now brunner2022 has been used only as part of an external
reference. It was never imputed or scored, and since Amendment 13 it is in no reference.

- **Data:** `data/datasets/brunner2022_holdout.h5ad` (built by `scripts/build_brunner2022_holdout.py`).
  - 434 HeLa single cells × 2476 proteins, 48.1% missing.
  - Cell-cycle groups UB/G1/G2/NB/TB; timsTOF DIA (DIA-NN); log2, per-cell median-centred.
- **Primary method `stack3_plain`:** kNN + low-rank + reference projection.
  - Reference: `explore_bio.reference_datasets()` (16 single-cell datasets, no holdouts) plus CCLE and ProteomeHD.
  - ALS rank 20, λ = 5, 15 iterations, ≥ 20 observations, κ = 0.
  - Simplex weights with step 0.25, chosen on a 10% inner mask of observed entries.
- **Design:** 30-cell subsamples (6 per cell-cycle group), seeds 7000–7009. MCAR and MNAR from `benchmarks/run.py::make_mask`
  on proteins observed in ≥ 50% of the subsample.
- **Endpoint:** RMSE on masked entries of complex-member proteins (`complexes.in_any_complex`).
- **Primary comparators:**
  - kNN;
  - the kNN + low-rank stack;
  - the mean of the `stack3_plain` pipelines with permuted reference loadings (seeds 0 and 1).
- **Pass, per comparator and mask:** the 95% paired-bootstrap CI (1000 resamples, seed 17) of ΔRMSE is entirely < 0, and
  ΔRMSE is ≤ −1% of the comparator's RMSE.
- **H14 is confirmed** only if all 6 primary comparisons pass.
- **Secondary:**
  - overall RMSE for the same comparisons;
  - BIM (Amendment 13) vs `stack3_plain`, and BIM vs `bim_null`, in-complex.
- **Disclosure:** H14 was formulated after dev results (Amendment 14). It is a replication attempt with a refined endpoint.
- **Single use:** `confirm_v7.py` refuses to run twice or with uncommitted code.
