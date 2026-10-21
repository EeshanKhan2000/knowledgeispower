# Preregistration: complex priors for single-cell proteomics reconstruction

Committed **before any benchmark code ran** (see this file's git timestamp vs. `results/`). Any
later deviation is listed under "Deviations" at the bottom with a reason. Results are reported
whichever way they come out.

## Claim under test
Curated protein-complex membership (CORUM, EBI Complex Portal) is a better prior for
reconstructing a cell's protein state from incomplete single-cell proteomics measurements than
data alone, than generic PPI networks (STRING), and than a degree-preserving shuffled version of
the same graph.

## Data
- **Dataset:** Petrosius et al. 2023 OCI-AML8227, Orbitrap Astral DIA. 215 cells × 2813 protein
  groups, 40.7% missing. 4 FACS-gated populations: LSC, prog, CD38_pos, CD38_neg. File and SHA-256
  in `data/PROVENANCE.md`. **No cell or protein filtering** beyond the eligibility rules below.
- **Priors:** `corum`, `complexportal` (edge = shared curated complex, weight = number of shared
  complexes); `string` (STRING v12.5 combined score ≥ 700, weight = score/1000); `string_exp`
  (experimental channel ≥ 700). The combined score includes co-expression and curated-database
  channels, so `string_exp` is the cleaner PPI comparison.
- **Nulls:** 10 degree-preserving double-edge-swap shuffles per prior (seeds 0–9; 10×|E| swaps;
  weights permuted onto the new edges).
- **"In-complex" stratum:** the protein group contains an accession that belongs to ≥ 1 CORUM or
  Complex Portal complex. Everything else is "not in complex".

## Methods
- **`prior` imputation:** per protein j, μ_j and σ_j are computed from observed values. Within a
  cell, the predicted z-score of a missing protein is the edge-weighted mean of its *observed*
  partners' z-scores, times one scalar β per graph. β is fitted by least squares on the
  *unmasked observed* entries only (each entry predicted from its partners, which never include
  itself). Estimate = μ_j + σ_j · β · ẑ. Entries with no observed partner fall back to kNN.
- **kNN baseline:** `scp_prep.impute.impute_knn`, k = 10, uniform weights.
- **Mean baseline:** column mean of observed values.
- **Panel selection** (candidates = proteins detected in ≥ 80% of cells):
  - `none`/HVP: top-k by variance of observed log2 values;
  - `soft_weight`: random walk with restart (restart probability α = 0.5, column-normalised
    weighted adjacency, dangling nodes keep their mass) seeded with the HVP variance scores,
    then top-k among candidates;
  - `random`: uniform among candidates, seeds 0–9.

## Tests and pass criteria
**Test 1 (headline): imputation of masked observed values.**
- Eligible proteins: detected in ≥ 50% of cells.
- Mask 10% of their observed entries under two masks, 5 seeds each (0–4):
  - **MCAR:** uniform;
  - **MNAR:** sampling weight = logistic((q25_j − x)/(0.5·σ_j)), favouring low intensities.
- Metrics on masked entries: RMSE and Pearson r, overall and per stratum.
- **Pass:** `corum` or `complexportal` has lower RMSE than kNN **and** than the mean of its own 10
  nulls, in the in-complex stratum, on both masks. "Lower" means the paired 95% bootstrap CI of
  the RMSE difference excludes 0. The bootstrap uses 1000 resamples of masked entries, pooled
  over seeds.

**Test 2: panel design.**
- k ∈ {25, 50, 100}.
- Features: the panel's columns from the kNN-imputed full matrix, standardised.
- Targets: all other proteins detected in ≥ 50% of cells. Training targets are kNN-imputed.
- Model: ridge (α = 1.0), 5-fold CV over cells (seed 0).
- Score: R² per target on held-out cells, **observed entries only**, averaged over targets
  (overall and per stratum).
- **Pass:** `soft_weight` with `corum`/`complexportal` beats HVP **and** the null mean, for at
  least 2 of 3 k.

**Test 3: stability.** For k = 50: 20 bootstrap resamples of cells (seeds 0–19), mean pairwise
Jaccard of the top-k. **Pass:** the complex prior is more stable than HVP and than its nulls.

**Test 4: complex vs. PPI.** Compare tests 1–3 across priors. **Pass:** corum/complexportal ≥
string_exp ≥ string on the test-1 in-complex RMSE.

**Sanity: classification.**
- Logistic regression (standardised, max_iter 5000) on the k = 50 panel, 5-fold stratified CV
  (seed 0), macro-F1.
- Reported only. If random selection reaches ≥ 0.9, it is flagged as a ceiling effect.

**Stretch: cross-context.** Select the panel on LSC + prog cells, then evaluate test 2 (k = 50)
on CD38_pos + CD38_neg cells.

**Discordance list.**
- Scope: in-complex proteins detected in ≥ 80% of cells.
- Statistic: Pearson r (pairwise complete, ≥ 30 cells) between the protein's z-scores and the
  weighted mean of its partners' z-scores in the union curated graph.
- Background: the same statistic on the 10 shuffled nulls.
- Ranked by discordance z = (null mean − r)/null sd, to `results/discordant_subunits.csv`.
- Labelled **hypotheses**, not findings.

## Reporting
Every row is reported, including losses. Results go to `results/*.json`, with fixed seeds. Total
runtime must stay under 30 min on a laptop.

## Deviations
*(none yet)*
