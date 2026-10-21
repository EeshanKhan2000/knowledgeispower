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
