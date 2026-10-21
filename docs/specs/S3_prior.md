# S3: extra prior source

> **Update 2026-10-21:** Complex Portal consistently beats CORUM as a partner source, and curated partners beat data-derived ones on Leduc (3–5%). **The priority question is whether hu.MAP 3.0 predicted complexes beat curated Complex Portal.** Baselines are a matched-edge data graph (`phase2.data_graph`) and degree-preserving nulls.

**Goal:** one more curated or data-derived complex prior, compared like-for-like with
CORUM / Complex Portal.

- **Candidates (verify each exists, its licence, and its download URL first):** hu.MAP 3.0
  complexes, BioPlex-derived communities, or an ontology-based grouping. Complex Portal already
  mixes in hu.MAP predictions, so state clearly how yours differs.
- **Where:** `contrib/s3_prior/`. Register with `register_prior("<name>", build, "...")`.
- `build(protein_ids)` returns a `networkx.Graph` that passes `validate_prior`, with
  `graph.graph['provenance']` (`source`, `version`, `url`, `sha256`). The `sha256` must match a
  row in `data/PROVENANCE.md`.
- The degree-preserving null is added automatically. Results land in `results/contrib/` via
  `python benchmarks/run.py --include-contrib`.
- **Contract:** `tests/contrib/test_s3_prior.py`.
- **Time box:** 3 h.
