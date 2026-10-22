"""Amendment-7 DEV: protein-specific kNN with knowledge-defined neighbourhoods. Dev seeds only, 30-cell regime.

    python benchmarks/explore_pknn.py   -> results/phase5/dev/dev_pknn.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_imc import SEEDS, TARGETS, blocks_for  # noqa: E402
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.imc import permuted_features  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(alphas=(0.5,), out_name="dev_pknn.json"):
    rows, t0 = [], time.time()
    for tname, loader, regimes in TARGETS:
        full = loader()
        names = list(full.var_names)
        Fc = blocks_for(tname, names)["curated_all"]
        N_cur = P.neighbour_sets_from_features(Fc)
        N_null = [P.neighbour_sets_from_features(permuted_features(Fc, s)) for s in (0, 1)]
        ct = full.obs["cell_type"].values
        types = sorted(set(ct))
        for n_cells in [r for r in regimes if r and r <= 30]:
            for kind in ["MCAR", "MNAR"]:
                for seed in SEEDS:
                    rng = np.random.default_rng(seed)
                    idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], n_cells // len(types), replace=False)
                                                  for c in types]))
                    X = np.asarray(full.X, float)[idx]
                    mask = make_mask(X, (~np.isnan(X)).mean(0) >= 0.5, kind, seed)
                    Xm = X.copy()
                    Xm[mask] = np.nan
                    truth = X[mask]
                    preds = {"knn": P._fill(Xm, P.loo_knn(Xm))}
                    Nd = P.neighbour_sets_from_data(Xm)
                    for a in alphas:
                        sfx = "" if a == 0.5 and len(alphas) == 1 else f"_a{a}"
                        preds[f"pknn_curated{sfx}"] = P.protein_specific_knn(Xm, N_cur, alpha=a)
                        preds[f"pknn_data{sfx}"] = P.protein_specific_knn(Xm, Nd, alpha=a)
                        for i, N in enumerate(N_null):
                            preds[f"pknn_null{i}{sfx}"] = P.protein_specific_knn(Xm, N, alpha=a)
                    for m, Y in preds.items():
                        e = Y[mask] - truth
                        rows.append({"target": tname, "n_cells": int(len(idx)), "mask": kind, "seed": seed,
                                     "method": m, "rmse_all": float(np.sqrt(np.mean(e ** 2)))})
                    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} ({time.time() - t0:.0f}s)", flush=True)
    (ROOT / "results" / "phase5" / "dev" / out_name).write_text(json.dumps({"seeds": SEEDS, "rows": rows}, indent=1) + "\n")
    import pandas as pd
    print(pd.DataFrame(rows).groupby(["target", "n_cells", "mask", "method"])["rmse_all"].mean().unstack("method").round(4).to_string())


if __name__ == "__main__":
    if "--sweep" in sys.argv:
        main(alphas=(0.1, 0.25), out_name="dev_pknn_sweep.json")
    else:
        main()
