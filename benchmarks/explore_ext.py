"""Amendment-4 DEV runs: priors with external (cross-dataset) evidence, leave-one-dataset-out.

    python benchmarks/explore_ext.py   -> results/phase4/dev/dev_ext.json  (+ summary table)

Targets: petrosius2023 (215 and 30 cells), leduc2022 and specht2021 (subsamples of 200 and 30 cells).
Dev seeds 100-102 only. The holdouts (khan2023, derks2022) are never touched.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import external as E  # noqa: E402
from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.datasets import load_leduc2022, load_petrosius2023, load_specht2021  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.priors import build_prior, shuffled_null  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [100, 101, 102]
TARGETS = [("petrosius2023", load_petrosius2023, [0, 30]), ("leduc2022", load_leduc2022, [200, 30]),
           ("specht2021", load_specht2021, [200, 30])]


def main():
    rows = []
    t0 = time.time()
    for tname, loader, regimes in TARGETS:
        full = loader()
        names = list(full.var_names)
        in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
        R, nds = E.pooled_corr(names, (tname,))
        cp = build_prior("complexportal", names)
        hm = build_prior("humap3", names)
        ne = cp.number_of_edges()
        ext = E.external_graph(names, R, ne)
        static = {"cp": cp, "cp_null0": shuffled_null(cp, 0), "cp_null1": shuffled_null(cp, 1),
                  "ext": ext, "cp_gated_ext": E.gate_by_external(cp, names, R),
                  "ext+cp": P.union_graph(ext, cp), "ext+cp_null0": P.union_graph(ext, shuffled_null(cp, 0)),
                  "humap3": hm, "humap3_null0": shuffled_null(hm, 0),
                  "humap3_gated_ext": E.gate_by_external(hm, names, R)}
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
                    eligible = (~np.isnan(X)).mean(0) >= 0.5
                    mask = make_mask(X, eligible, kind, seed)
                    Xm = X.copy()
                    Xm[mask] = np.nan
                    truth = X[mask]
                    _, cols = np.nonzero(mask)
                    sel = in_cx[cols]

                    def score(method, graph, filled):
                        e = filled[mask] - truth
                        rows.append({"target": tname, "n_cells": int(len(idx)), "mask": kind, "seed": seed,
                                     "method": method, "graph": graph,
                                     "rmse_in_complex": float(np.sqrt(np.mean(e[sel] ** 2))),
                                     "rmse_all": float(np.sqrt(np.mean(e ** 2)))})

                    K = P.loo_knn(Xm)
                    LR = P.grmf(Xm, None, names, lam_g=0.0, full=True)
                    score("knn", "-", P._fill(Xm, K))
                    score("lowrank", "-", P._fill(Xm, LR))
                    graphs = dict(static)
                    graphs["data_in"] = P.data_graph(Xm, names, ne)
                    for gname, g in graphs.items():
                        score("E1", gname, P.residual_on_knn(Xm, g, names, K=K))
                        score("E6", gname, P.residual_on_knn(Xm, g, names, K=LR))
                    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} ({time.time() - t0:.0f}s)", flush=True)
    out = ROOT / "results" / "phase4" / "dev"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev_ext.json").write_text(json.dumps({"seeds": SEEDS, "rows": rows}, indent=1) + "\n")
    import pandas as pd

    df = pd.DataFrame(rows)
    t = df.groupby(["target", "n_cells", "mask", "method", "graph"])["rmse_in_complex"].mean().unstack(["method", "graph"])
    print(t.round(4).T.to_string())


if __name__ == "__main__":
    main()
