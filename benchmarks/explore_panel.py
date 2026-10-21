"""Phase-2 DEVELOPMENT runs for panel design (P1 + W1). CV seeds 100-102 only (see EXPLORATION.md).

    python benchmarks/explore_panel.py   -> results/phase2/dev/dev_panel.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import KS, panel_r2  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.datasets import load_petrosius2023  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.methods import candidates, knn_fill, select_features, select_random  # noqa: E402
from scp_graphfs_mcp.priors import build_prior, shuffled_null  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV_SEEDS = [100, 101, 102]


def main():
    adata = load_petrosius2023()
    names = list(adata.var_names)
    X = np.asarray(adata.X, float)
    Xknn = knn_fill(adata)
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    target = (~np.isnan(X)).mean(0) >= 0.5
    kmask = P.keratin_mask(names)
    cand = candidates(adata) & ~kmask
    graphs = {n: build_prior(n, names) for n in ["corum", "complexportal"]}
    rows = []
    t0 = time.time()
    for k in KS:
        panels = {"hvp": select_features(adata, None, k, "none"),
                  "hvp_W1": [p for p in select_features(adata, None, k + 60, "none") if not kmask[names.index(p)]][:k],
                  "pivqr_W1": P.select_pivoted_qr(Xknn, names, k, cand)}
        for s in range(10):
            panels[f"random__{s}"] = select_random(adata, k, s)
        for n, g in graphs.items():
            panels[f"cover_{n}_W1"] = P.select_coverage(X, g, names, k, exclude=kmask)
            for i in range(3):
                panels[f"cover_{n}__null{i}_W1"] = P.select_coverage(X, shuffled_null(g, i), names, k, exclude=kmask)
            dg = P.data_graph(X, names, g.number_of_edges())
            panels[f"cover_data_matched_{n}_W1"] = P.select_coverage(X, dg, names, k, exclude=kmask)
        for m, panel in panels.items():
            idx = [names.index(p) for p in panel]
            for s in DEV_SEEDS:
                r = panel_r2(Xknn, X, idx, target, in_cx, seed=s)
                rows.append({"k": k, "method": m, "cv_seed": s, **{f"r2_{a}": v for a, v in r.items()},
                             "n_keratin": int(kmask[idx].sum())})
        print(f"[{time.strftime('%H:%M:%S')}] k={k} done ({time.time() - t0:.0f}s)", flush=True)
    out = ROOT / "results" / "phase2" / "dev"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev_panel.json").write_text(json.dumps({"cv_seeds": DEV_SEEDS, "rows": rows}, indent=1) + "\n")
    import pandas as pd

    df = pd.DataFrame(rows)
    df["base"] = df["method"].str.replace(r"__(null|)\d+", lambda mm: "__null" if "null" in mm.group(0) else "__rand", regex=True)
    print(df.groupby(["k", "base"])[["r2_all", "r2_in_complex", "n_keratin"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
