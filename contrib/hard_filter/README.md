# Hard-filter selection arm (Collaborator A)

**Question:** is it better to *use the prior as a hard filter* (only choose proteins in the
graph), to *use it as a soft weight* (`soft_weight`: propagate data scores over the graph), or to
ignore it (`none`)?

## Interface
`select(adata, graph, k) -> list[str]` (k var_names), registered with
`register_method("hard_filter", ..., select=select)` in `contrib/hard_filter/__init__.py`. The
core `select_features(..., mode="hard_filter")` dispatches to it once it's registered.

## Spec
1. Candidates = proteins detected in ≥ 80% of cells (`scp_graphfs_mcp.methods.candidates`).
2. Filter = candidates with degree ≥ 1 in `graph`.
3. Rank the filtered set by HVP score (`scp_graphfs_mcp.methods.hvp_scores`), descending. Break
   ties by var order.
4. If fewer than k pass the filter, fill the remaining slots with the highest-HVP candidates
   outside the filter, and log how many were filled.
5. Deterministic: no randomness.

## Contract
`tests/test_hard_filter.py`: xfail until registered. Benchmark rows appear only with
`python benchmarks/run.py --include-contrib`, written to `results/contrib/`.

## Update 2026-10-21 (findings that affect this arm)
- **Contaminants:** HVP rankings are dominated by contaminants (8 keratins in 25). Apply `scp_graphfs_mcp.phase2.keratin_mask(var_names)` before ranking. This is the W1 filter, built from the HGNC "Keratins" gene groups.
- **Random beats HVP:** random panels beat HVP and propagation panels (R² ≈ 0.45 vs ≈ 0.21 at k = 25). A hard filter that ranks by HVP may therefore lose to random too, so report it against random.
- **Coverage is a useful comparator:** greedy coverage over curated complexes (`phase2.select_coverage`) ≈ random, and beats its null.
- **Dev only:** evaluate with `benchmarks/explore_panel.py`-style CV seeds 100–102. The datasets are dev-only for new claims (see `docs/SLOTS.md`).
