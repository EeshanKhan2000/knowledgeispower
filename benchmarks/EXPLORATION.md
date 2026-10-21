# Exploration protocol (phase 2): develop on dev masks, confirm once on held-out masks

The preregistered phase-1 result (`benchmarks/PREREGISTRATION.md`, `results/`) **stands as reported**:
the curated priors beat their shuffled nulls, but they lose to kNN. This file fixes, *before any phase-2 run*,
how we look for a method that might make the claim true without fooling ourselves.

## Why a protocol
If we try ideas until one beats kNN on the same masks, we overfit the benchmark: a forking-paths
problem. So we split the masks:

| Use | Mask seeds | Masks | Who sees the numbers |
|---|---|---|---|
| Phase 1 (done) | 0–4 | MCAR, MNAR | already public |
| **Development** | **100, 101, 102** | MCAR, MNAR | used freely to try ideas, logged in `docs/EXPLORATION_LOG.md` |
| **Confirmation** | **1000–1004** | MCAR, MNAR | used **once**, after `benchmarks/PREREGISTRATION_v2.md` is committed |

The mask generator, eligible proteins (detected in ≥ 50% of cells), mask fraction (10%) and strata are
identical to phase 1.

## Fair "data alone" baselines (stronger than phase 1)
The claim is "curated complexes are a better prior than data alone". Every graph-based idea is
therefore run on four kinds of graph:
1. **CORUM** and **Complex Portal** (curated);
2. **their degree-preserving nulls** (seeds 0–9);
3. **a data-derived co-variation graph:** for each protein, its most-correlated proteins in the
   *masked training matrix* (pairwise-complete Pearson), with the same total edge count as Complex
   Portal. This is the strongest "data alone" neighbour set;
4. **STRING** (combined and experimental).

On top of these, kNN (k = 10) stays a baseline. A phase-2 method supports the claim only if, on the
confirmation masks and in the in-complex stratum, the curated version beats **kNN, its own null, and
the data-derived graph**, with paired 95% bootstrap CIs excluding 0 on both masks.

## Ideas to try (cross-domain analogies)
| ID | Idea | Analogy |
|---|---|---|
| E1 | **Residual-on-kNN:** kNN gives each cell's state; partners explain what kNN misses. x̂ = kNN + β · (edge-weighted mean of partners' kNN residuals in the same cell) | Gradient boosting / residual learning; "baseline + correction" in sensor fusion |
| E2 | **Stoichiometric offsets:** slope-1 log-ratio model per edge, x̂_j = mean_k (x_k + δ_jk), where δ_jk is the training median of x_j − x_k | Mass balance / conserved ratios in chemistry; fixed isotope ratios |
| E3 | **Graph-regularised low-rank completion:** X ≈ U Vᵀ with a Laplacian penalty tr(Vᵀ L V) over the protein graph | Netflix-style recommender systems with a social/item graph (GRMF) |
| E4 | **Edge reliability gating:** reweight each prior edge by its training co-variation, shrunk toward the prior weight; the prior restricts *which* pairs may be used | Attention restricted by a mask; trust calibration; Kalman gain by measured precision |
| E5 | **Inverse-variance fusion of kNN and partner estimates,** per protein, from training residual variances | Meta-analysis / sensor fusion (inverse-variance weighting) |
| W1 | **Contaminant filter** (keratins etc.) before panel selection | Data hygiene (cRAP lists in proteomics) |
| P1 | **Panel as sensor placement:** greedy submodular coverage of complexes vs. data-only greedy column subset selection | Sensor placement / facility location; pivoted-QR column selection |

## Rules
- Every idea's dev result is logged, including failures, in `docs/EXPLORATION_LOG.md` and on its GitHub issue.
- Hyperparameters are tuned on dev masks only.
- **Selection rule (fixed now):** choose the *single* imputation method with the lowest dev in-complex RMSE
  (averaged over both masks), among methods whose curated version beats kNN, its null and the data graph
  on dev. If none qualifies, we report that and do not run confirmation as a "win".
- Before the confirmation run, `benchmarks/PREREGISTRATION_v2.md` is committed with the chosen method,
  hyperparameters, baselines and pass criteria. The confirmation masks are run once.
- Phase-2 outputs go to `results/phase2/` (dev runs to `results/phase2/dev/`).

## Amendment 1 (committed before the runs it covers)

Dev seed 100, MCAR, was already run (in `results/phase2/dev/dev_results_quick.json`). It showed:
- residual-on-kNN with curated graphs beats kNN and the null, but the data-derived graph and STRING beat it;
- low-rank completion (E3) beats everything, and graph regularisation adds nothing over its null.

Before running more, three dev dimensions are added:
1. **Low-data regime (prior-matters-most hypothesis; analogies: recommender cold-start, Bayesian shrinkage).**
   - Subsample n_cells ∈ {30, 60} (cell-subsample seeds = mask seed; stratified by cell type), then mask
     within the subsample.
   - The data-derived graph and kNN use only those cells. The curated prior is unchanged.
2. **Prior + data (does the prior add information beyond the data?).** Graphs: union(data-derived,
   curated) vs. union(data-derived, null) vs. data-derived alone.
3. **E6 = residual correction on a low-rank base:** x̂ = GRMF + β · partner-weighted GRMF residuals.

**Scoping rule:** if the only qualifying method wins in a regime (e.g. n_cells ≤ 60), the v2
preregistration states that regime, and the README reports the claim *as scoped*. The phase-1
full-data result stays as reported.

## Amendment 2: an independent held-out dataset (committed before any evaluation on it)

Repeated seeds on the same 215 cells can't fully remove forking-path risk, so we add an **independent
dataset**: Leduc et al. 2022 (nPOP/pSCoPE), melanoma + monocytes, the **pre-imputation** protein assay
`proteins_norm2`. That's 1543 cells and 65.9% missing; provenance is in `data/PROVENANCE.md`.

- It's built from the scpdata `.Rda` without R (`scripts/rda_extract_leduc.py`, `scripts/build_leduc2022.py`).
- **No method has been evaluated on it.** No imputation, panel or correlation analysis may be run on it
  until `benchmarks/PREREGISTRATION_v3.md` is committed. v3 fixes the method(s) using Petrosius
  evidence only (dev + v2 confirmation).
- Allowed before v3: shape, missingness and label counts (already printed by the build script).
