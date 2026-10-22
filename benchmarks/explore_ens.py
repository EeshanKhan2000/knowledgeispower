"""Amendment-6 DEV: ensemble of kNN and knowledge-IMC (w = 0.5 fixed). Dev seeds 100-102 only.

    python benchmarks/explore_ens.py   -> results/phase5/dev/dev_ens.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_imc import SEEDS, TARGETS, blocks_for  # noqa: E402
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.imc import imc, permuted_features  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W = 0.5


def main():
    rows = []
    t0 = time.time()
    for tname, loader, regimes in TARGETS:
        full = loader()
        names = list(full.var_names)
        B = blocks_for(tname, names)
        Fc = B["curated_all"]
        Fnull = [permuted_features(Fc, s) for s in (0, 1)]
        ct = full.obs["cell_type"].values
        types = sorted(set(ct))
        for n_cells in regimes:
            for kind in ["MCAR", "MNAR"]:
                for seed in SEEDS:
                    if n_cells:
                        rng = np.random.default_rng(seed)
                        idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], n_cells // len(types), replace=False)
                                                      for c in types]))
                    else:
                        idx = np.arange(full.n_obs)
                    X = np.asarray(full.X, float)[idx]
                    mask = make_mask(X, (~np.isnan(X)).mean(0) >= 0.5, kind, seed)
                    Xm = X.copy()
                    Xm[mask] = np.nan
                    truth = X[mask]
                    K = P._fill(Xm, P.loo_knn(Xm))
                    preds = {"knn": K, "imc_curated": imc(Xm, Fc),
                             "imc_nofeat": imc(Xm, np.zeros((len(names), 1)))}
                    for i, Fn in enumerate(Fnull):
                        preds[f"imc_null{i}"] = imc(Xm, Fn)
                    for k in ["imc_curated", "imc_nofeat", "imc_null0", "imc_null1"]:
                        preds[f"ens_{k}"] = (1 - W) * K + W * preds[k]
                    for m, Y in preds.items():
                        e = Y[mask] - truth
                        rows.append({"target": tname, "n_cells": int(len(idx)), "mask": kind, "seed": seed,
                                     "method": m, "rmse_all": float(np.sqrt(np.mean(e ** 2)))})
                    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} ({time.time() - t0:.0f}s)", flush=True)
    out = ROOT / "results" / "phase5" / "dev"
    (out / "dev_ens.json").write_text(json.dumps({"seeds": SEEDS, "w": W, "rows": rows}, indent=1) + "\n")
    import pandas as pd

    print(pd.DataFrame(rows).groupby(["target", "n_cells", "mask", "method"])["rmse_all"].mean().unstack("method").round(4).to_string())


if __name__ == "__main__":
    main()
