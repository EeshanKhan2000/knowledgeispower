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
