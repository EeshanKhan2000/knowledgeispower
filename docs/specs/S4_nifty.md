# S4: NIFty baseline wrapper

NIFty (missingness-tolerant single-cell proteomics feature selection) has public code at
https://github.com/PayneLab/nifty (verified 2026-10-21; see `docs/prior-art.json`).

- **Wrap it** as a contrib method: `register_method("nifty", ..., select=select)` in
  `contrib/s4_nifty/`. `select(adata, graph, k)` ignores the graph and returns k var_names.
- **Dependencies:** none of NIFty's may enter the core `pyproject.toml`. Use an optional import
  and skip cleanly if it isn't installed. Get Amit's approval for any extra.
- **Acceptance:**
  - `python benchmarks/run.py --include-contrib` produces `nifty:*` panel rows in
    `results/contrib/panel.json`;
  - a test in `tests/contrib/test_s4_nifty.py` checks determinism and that it returns k unique
    candidates.
- **Time box:** 3 h.
