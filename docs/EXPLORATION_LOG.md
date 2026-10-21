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
