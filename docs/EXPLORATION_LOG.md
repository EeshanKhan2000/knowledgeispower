# Phase-2 exploration log (dev masks / dev CV seeds only)

Protocol: `benchmarks/EXPLORATION.md`. Every result goes here, including failures. Raw numbers are in
`results/phase2/dev/`. These are **development** numbers: they guide the choice of method and are
**not** evidence for the claim.

## 2026-10-21 · P1 + W1: panel design as sensor placement (issue #6)
Run with `python benchmarks/explore_panel.py` (CV seeds 100–102, all 215 cells). Values are mean held-out R² over targets.

| k | HVP | HVP + W1 | pivoted QR + W1 | random (10) | coverage CORUM + W1 | its null (3) | coverage data graph (matched) |
|---|---|---|---|---|---|---|---|
| 25 | 0.213 | 0.218 | 0.367 | 0.447 | 0.452 | 0.314 | 0.487 |
| 50 | 0.199 | 0.340 | 0.368 | 0.416 | 0.406 | 0.329 | 0.449 |
| 100 | 0.237 | 0.228 | 0.178 | 0.243 | 0.261 | 0.267 | 0.292 |

(Complex Portal coverage is close to CORUM's; see the JSON.)

**Read:**
- **W1 (keratin filter):** HVP puts 8 keratins in 25 slots; the filter fixes that.
- **Structure is real:** greedy coverage over curated complexes beats its own degree-preserving null by about 0.08–0.14 R² at k = 25–50.
- **Not better than data or random:** curated coverage only *ties* random panels, and coverage over a data-derived co-variation graph beats both.
- **Caveat:** the data graph is built on all cells, a mild leak in its favour.
- **Verdict on dev:** P1 does not qualify under the selection rule, because the data-derived graph wins.

## 2026-10-21 · Imputation ideas E1–E6, dev grid (issues #2–#5)
Run: `python benchmarks/explore.py --n-cells 0 60 30`. In-complex RMSE, mean over dev seeds 100–102.
Raw rows: `results/phase2/dev/dev_results.json`.

**All 215 cells.** Each cell shows MCAR / MNAR; the "data graph" column is the matched-edge data-derived co-variation graph.

| Method (curated graph) | Curated | Its null (3) | Data graph | kNN | Low-rank, no graph |
|---|---|---|---|---|---|
| E1 residual-on-kNN (Complex Portal) | 0.672 / 0.747 | 0.684 / 0.756 | 0.681 / 0.776 | 0.687 / 0.762 | 0.659 / 0.723 |
| E1+E4 gated (Complex Portal) | 0.671 / 0.746 | 0.684 / 0.754 | 0.681 / 0.776 | 〃 | 〃 |
| E2 stoich-on-kNN (Complex Portal) | 0.677 / 0.754 | 0.687 / 0.761 | 0.684 / 0.773 | 〃 | 〃 |
| E5 fused (Complex Portal) | 0.671 / 0.750 | 0.694 / 0.768 | 0.674 / 0.766 | 〃 | 〃 |
| E6 residual-on-low-rank (Complex Portal) | 0.656 / 0.720 | 0.659 / 0.723 | 0.658 / 0.722 | 〃 | 〃 |
| E3 low-rank + Laplacian (CORUM) | 0.640 / 0.720 | 0.641 / 0.721 | 0.654 / 0.723 | 〃 | 〃 |

**Read (all cells):**
- **Kinship structure matters most.** Every kNN-based variant with Complex Portal beats kNN, its null and the data graph on both masks. That is the first time the curated prior beats "data neighbours" on this benchmark.
- **But a plain low-rank model beats them all**, so they still lose to the strongest data-alone baseline.
- **E6 (curated residuals on top of low-rank) beats low-rank, its null and the data graph,** by about 0.003 RMSE.
- **E3's graph penalty helps,** but its null does almost as well (Δ ≈ 0.0005): this is mostly Laplacian regularisation, not curation.

**Low-n regimes: BUG FOUND, rerun pending.** `data_graph` required ≥ 30 co-observed cells per pair. That is impossible at 28 cells, so the data graph was empty and "data" collapsed to kNN. It is also restrictive at 60 cells. Fix: threshold = min(30, max(5, n/2)), unchanged at 215 cells. The low-n numbers from this run are **void** and will be replaced by the rerun (`dev_results_lown_fixed.json`).

**Selection (rule fixed in `EXPLORATION.md` before these runs):**
- **Eligible:** among methods whose curated version beats kNN, its null and the data graph on dev (215 cells, both masks), the lowest mean RMSE is **E3 low-rank + Laplacian with CORUM** (0.680).
- **Chosen:** it goes to confirmation (`PREREGISTRATION_v2.md`). Its dev margin over its own null is tiny, so we expect the confirmation to **fail** on the null comparison. We follow the rule regardless.

## 2026-10-21 · v2 CONFIRMATION (seeds 1000–1004, single run; `results/phase2/confirm/confirm_v2.json`)

**Primary (E3 low-rank + CORUM Laplacian): NOT CONFIRMED, 6/8 comparisons.** It beats kNN, low-rank-no-graph
and the data graph on both masks. It does **not** beat its own shuffled null:
- MCAR Δ = −0.0007 [−0.0031, +0.0016]
- MNAR Δ = +0.0001 [−0.0018, +0.0017]

The Laplacian helps through regularisation, not curation. This is the outcome predicted from dev.

**Secondary (reported, not claimed):**
- **E6, Complex Portal residuals on a low-rank base,** beats low-rank, its own null and the data graph on **both** masks, with all CIs excluding 0:

  | E6 (Complex Portal) vs. | MCAR ΔRMSE [95% CI] | MNAR ΔRMSE [95% CI] |
  |---|---|---|
  | Low-rank, no graph | −0.0033 [−0.0039, −0.0028] | −0.0030 [−0.0035, −0.0025] |
  | Own null | −0.0033 [−0.0039, −0.0028] | −0.0030 [−0.0035, −0.0025] |
  | Data-derived graph | −0.0026 [−0.0032, −0.0019] | −0.0016 [−0.0021, −0.0010] |

  The effect is small (~0.5% of RMSE). Its null gives the same RMSE as the low-rank base, so null "partners" add nothing (fitted β ≈ 0).
- **E1+E4** (gated, kNN base) beats kNN, its null and the data graph, but loses to low-rank.
- **E3 with STRING** has the lowest RMSE of all (MCAR 0.627, MNAR 0.706). It was not part of any pass test.

**What this suggests:** E6 is a candidate for an **independent** test. Next: `PREREGISTRATION_v3.md` on the
held-out Leduc 2022 dataset, chosen from Petrosius evidence only.

## 2026-10-21 · Low-data regimes, rerun with the data-graph fix (`dev_results_lown_fixed.json`)
In-complex RMSE, dev seeds 100–102, for E1+E4 (gated residual-on-kNN) with Complex Portal:

| Cells | Mask | data + CP | data + null | data alone | CP alone | kNN | low-rank |
|---|---|---|---|---|---|---|---|
| 28 | MCAR | **0.841** | 0.871 | 0.883 | 0.864 | 0.922 | 1.046 |
| 28 | MNAR | **0.861** | 0.874 | 0.904 | 0.876 | 0.932 | 1.065 |
| 60 | MCAR | **0.759** | 0.777 | 0.772 | 0.779 | 0.813 | 0.802 |
| 60 | MNAR | **0.849** | 0.856 | 0.869 | 0.854 | 0.886 | 0.889 |

**Read:**
- **Low-rank collapses with few cells,** so kNN-based stacking is the right base there.
- **Complex Portal adds information beyond the data graph:** data + CP beats data + null and data alone in every cell of the table.
- **CORUM is mixed:** at n = 28 MNAR, data + null (0.828) ≤ data + CORUM (0.835).

This motivates **v4** (low-data regime, independent Leduc dataset). v4 was preregistered *before* the v3 result was known.

## 2026-10-21 · v4 CONFIRMATION (Leduc 2022, low-data regime; `results/phase3/confirm_v4.json`)

**Primary: NOT CONFIRMED (2/6).** At n = 30 cells, data + Complex Portal:
- **vs. data + null:** beats it on MCAR (−1.05%, CI excludes 0). On MNAR the CI includes 0 (−0.35%).
- **vs. data alone:** beats it on MCAR (−0.50%). On MNAR the CI includes 0.
- **vs. kNN: loses on both masks** (+6.25% MCAR, +2.93% MNAR). On Leduc, residual correction on top of kNN *hurts*, whatever the graph.

**Secondary, worth recording (consistent across all 4 regime × mask cells, CIs excluding 0):** using **Complex Portal
partners alone** gives lower error than using **data-derived co-variation partners**. Both are in the same residual-on-kNN model, and both are still worse than kNN:

| Cells | Mask | Complex Portal partners vs. data-derived partners |
|---|---|---|
| 30 | MCAR | −5.3% RMSE |
| 30 | MNAR | −2.8% RMSE |
| 60 | MCAR | −4.7% RMSE |
| 60 | MNAR | −3.7% RMSE |

**Mixed:** CORUM gives −2.3% / −2.1% at n = 60, but at n = 30 it is not better (−0.2%, CI includes 0) and is worse on MNAR (+0.7%).

**Read:** on an independent dataset with few cells, curated complexes are a *better choice of partners* than
partners estimated from the data. However, the partner-residual model itself doesn't beat kNN here.

## 2026-10-21 · v3 CONFIRMATION (Leduc 2022, all 1543 cells; `results/phase3/confirm_v3.json`)

**Primary: passes the preregistered criterion (8/8), but the effect is practically negligible.**

| E6 + Complex Portal vs. (in-complex) | MCAR | MNAR |
|---|---|---|
| Low-rank base | −0.01% RMSE | −0.01% |
| Own null | −0.01% | −0.01% |
| Data-derived graph | −0.14% | −0.07% |
| kNN | −1.00% | −0.98% |

**Why "passes" overstates it:**
- **The correction is tiny:** the fitted correction weight is β ≈ 0.02 on every seed, so curated partners barely change the low-rank estimate.
- **The CIs are optimistic:** separation comes from pooling ~100k masked entries with correlated errors.
- **The kNN gain isn't the prior's:** the ~1% gain over kNN comes from the low-rank base.

**Process error, disclosed:** v3 had no *smallest effect size of interest*. With one, for example 1% of RMSE, the primary
would **fail** against the base and the null. We report it as: *passes the letter of v3, not its spirit*.

**Consistent signal across both datasets:** curated partners beat data-derived partners. This holds for
v3 vs. the data graph (small), v4 secondary (3–5% at 30–60 cells), Petrosius v2 secondary and Petrosius dev.
That is the defensible, narrower form of "better than data alone": *as the source of which proteins inform
a missing one*. It is not a claim that the curated prior beats the best data-only imputer.

## 2026-10-21 · v5 CONFIRMATION (SCoPE2, third dataset, SESOI 1%; `results/phase3/confirm_v5.json`)

**Primary: NOT CONFIRMED (0/4).** At n = 30, Complex Portal partners vs. data-derived partners:

| Mask | Δ RMSE | 95% CI | % of reference | Pass? |
|---|---|---|---|---|
| MCAR | −0.0043 | [−0.0104, +0.0016] | −0.78% | fails (CI includes 0 and below the 1% SESOI) |
| MNAR | −0.0063 | [−0.0121, −0.0004] | −0.95% | fails (below the 1% SESOI) |

Against its own null: −0.38% (MCAR) and −0.21% (MNAR), both with CIs including 0.

**Secondary:**
- **At n = 60,** Complex Portal beats data-derived partners by −1.45% (MCAR) and −1.48% (MNAR), with CIs excluding 0.
- **CORUM partners are worse than data-derived partners** on SCoPE2 (+3.7% at n = 30, MCAR).
- **No graph-based variant meaningfully beats kNN.**

**Where the evidence stands after three datasets:**
1. **Robust:** curated complex graphs carry real signal. They beat degree-preserving shuffles across tests and datasets (phase 1, v4, v5 n = 60), though the gain is often small.
2. **Directionally consistent but small, and not confirmed at a 1% SESOI:** Complex Portal partners beat
   data-derived partners. That's 3–5% on Leduc, ~1% on SCoPE2, and it isn't true for CORUM on SCoPE2.
3. **Not supported:** that a curated prior gives a *better imputer than data alone*. kNN or low-rank models match or beat
   every prior-based method by any practically meaningful margin, on all three datasets.

Further attempts on these three datasets would be forking paths. A new claim needs new data.

## 2026-10-21 · Amendment 4 dev: external-evidence priors (`results/phase4/dev/dev_ext.json`)

**Setup:** leave-one-dataset-out over the 5-dataset corpus. Petrosius uses 215/28 cells; Leduc and SCoPE2 use subsamples of 200/30. Dev seeds 100–102.
Each prior graph was tested in residual-on-kNN (E1) and residual-on-low-rank (E6). The priors were:
- Complex Portal (CP);
- CP gated by external co-variation;
- the external-only graph;
- external ∪ CP, vs. external ∪ CP-null;
- hu.MAP 3.0, alone and gated;
- an in-dataset data graph.

**Findings:**
- **External co-variation adds nothing.** The external-only graph never beats kNN or low-rank, gating CP by external
  evidence never beats plain CP, and ext ∪ CP is worse than CP alone.
  - Curated CP edges do have higher external correlation than random pairs (median r 0.057 vs 0.003), so the evidence is real but weak.
- **On Leduc and SCoPE2, every partner correction is ≈ 0.** RMSE equals the kNN or low-rank base to 3 decimals; β ≈ 0.
- **Only Petrosius at 28 cells shows a gain:** CP + E1 gives 0.862 / 0.878 vs. best data-only 0.884 / 0.905 (MCAR / MNAR). This is the
  dataset that motivated v4 and v5, which did not replicate.
- **hu.MAP 3.0 ≈ CP** wherever there is any signal.

**Selection rule (Amendment 4): no method qualifies.** No curated variant beats all baselines across corpus targets.
Following the rule, **v6 is not run as a win**, and khan2023 stays an untouched holdout for a future, different idea.

## 2026-10-22 · Amendment 5 dev: knowledge features in side-information MF (`results/phase5/dev/dev_imc.json`)
Overall RMSE, mean over dev seeds 100–102. "curated_all" = GO + HPA + UniProt keywords + PaxDb/length/mass + spectral
embeddings of Complex Portal and STRING.

| Target, cells | kNN | low-rank | IMC, no features | IMC, shuffled features | IMC, curated_all |
|---|---|---|---|---|---|
| Leduc 30, MCAR / MNAR | **0.546 / 0.633** | 0.835 / 0.868 | 0.725 / 0.772 | 0.682 / 0.742 | 0.664 / 0.733 |
| SCoPE2 30 | **0.551 / 0.646** | 0.912 / 0.943 | 0.765 / 0.831 | 0.710 / 0.773 | 0.692 / 0.764 |
| Petrosius 28 | 0.981 / 0.962 | 1.126 / 1.131 | 0.994 / 1.003 | 0.933 / 0.970 | **0.891 / 0.936** |
| at 200 / 215 cells | ≈ everything equal (±0.01) | | | | |

**Read:**
- **Knowledge features beat shuffled features in every 30-cell cell.** Combining sources is best, and no single source is enough.
- **But kNN dominates the low-rank family at 30 cells** on Leduc and SCoPE2.
- **Rule outcome:** IMC qualifies on 1 of 3 targets, so no v6 is run.

## 2026-10-22 · Amendment 6 dev: kNN + knowledge-IMC ensemble, w = 0.5 (`results/phase5/dev/dev_ens.json`)
Overall RMSE, dev seeds 100–102.

| Target, cells | kNN | ensemble (curated) | null ensemble (shuffled features) | kNN + IMC (no features) |
|---|---|---|---|---|
| Leduc 30, MCAR / MNAR | **0.546 / 0.633** | 0.566 / 0.648 | 0.572 / 0.653 | 0.582 / 0.657 |
| SCoPE2 30 | **0.551 / 0.646** | 0.565 / 0.653 | 0.576 / 0.665 | 0.593 / 0.681 |
| Petrosius 28 | 0.981 / 0.962 | 0.878 / 0.897 | **0.876** / 0.900 | 0.893 / 0.907 |
| Leduc 200 | 0.503 / 0.594 | 0.492 / 0.584 | 0.491 / 0.585 | **0.490 / 0.584** |
| SCoPE2 200 | 0.509 / 0.611 | 0.486 / 0.575 | 0.487 / 0.576 | **0.484 / 0.575** |

**Read:**
- **At 30 cells,** blending with knowledge-IMC makes kNN *worse* on Leduc and SCoPE2. The knowledge-feature ensemble does beat the shuffled-feature ensemble by 0.8–1.9%, so the knowledge signal is consistent but too weak to lift a strong kNN.
- **At 200 cells and on Petrosius,** ensembles beat kNN through model averaging, and the no-feature and shuffled ensembles do just as well.
- **Rule: does not qualify on any target.** No v6 is run, and khan2023 stays untouched.

## Overall status after Amendments 4–6 (2026-10-22 00:00 ET)
Nine distinct approaches have been tried, including:
- edge corrections;
- graph-regularised MF;
- residual stacking;
- curated × external gating;
- hu.MAP 3.0;
- a pooled 5-dataset corpus;
- knowledge feature representations from GO, HPA, UniProt, PaxDb, and spectral STRING/CP embeddings;
- kNN ensembles.

They were tested across 5 datasets, with 4 single-use confirmations. The pattern is the same throughout:
- **knowledge priors carry real, reproducible structure** (they beat shuffled versions in nearly every test);
- **they do not beat strong data-only imputers (kNN or low-rank) by a meaningful margin.**

## 2026-10-22 · Amendment 7 dev: protein-specific kNN, knowledge neighbourhoods, α = 0.5 (`results/phase5/dev/dev_pknn.json`)
Overall RMSE at 30 cells (Petrosius 28), mean over dev seeds; change of the curated version relative to each comparator:

| Target / mask | kNN | pkNN curated | vs kNN | vs null neighbourhoods | vs data neighbourhoods |
|---|---|---|---|---|---|
| Leduc MCAR | 0.546 | 0.552 | +1.1% | −1.4% | −1.3% |
| Leduc MNAR | 0.633 | 0.639 | +0.9% | −1.1% | −1.6% |
| Petrosius MCAR | 0.981 | **0.955** | −2.7% | −3.9% | −1.9% |
| Petrosius MNAR | 0.962 | **0.940** | −2.4% | −3.6% | −5.1% |
| SCoPE2 MCAR | 0.551 | 0.554 | +0.6% | −1.1% | −1.7% |
| SCoPE2 MNAR | 0.646 | 0.648 | +0.2% | −1.3% | +0.3% |

**Read:**
- **Knowledge-defined neighbourhoods beat shuffled ones in every case, and beat data-defined ones in 5/6.**
- **They beat plain kNN only on Petrosius.** On Leduc and SCoPE2 they are within ~1% of kNN.
- **Rule: qualifies on 1 of 3, so it does not qualify.** It is the closest approach so far.
