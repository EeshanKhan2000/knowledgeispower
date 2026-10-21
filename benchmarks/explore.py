"""Phase-2 DEVELOPMENT runs (dev mask seeds only). See benchmarks/EXPLORATION.md.

    python benchmarks/explore.py            # -> results/phase2/dev/dev_results.json (+ printed table)
    python benchmarks/explore.py --quick    # 1 seed, 1 null, MCAR only

Refuses confirmation seeds: those are run only by the v2 confirmation script, once.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import make_mask  # noqa: E402  (identical mask generator to phase 1)

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.datasets import from_log2_matrix, load_petrosius2023  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.methods import knn_fill  # noqa: E402
from scp_graphfs_mcp.priors import build_prior, shuffled_null  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV_SEEDS = [100, 101, 102]
CONFIRM_SEEDS = set(range(1000, 1005))


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def methods_for(kind):
    """(label, fn(X, graph, names, K)) per graph kind."""
    m = [("E1_residual", lambda X, g, n, K: P.residual_on_knn(X, g, n, K)),
         ("E1E4_gate1", lambda X, g, n, K: P.residual_on_knn(X, g, n, K, gate=1.0)),
         ("E2_stoich_on_knn", lambda X, g, n, K: P.stoich_on_knn(X, g, n, K)),
         ("E5_fused", lambda X, g, n, K: P.fused(X, g, n, K))]
    if kind in ("curated", "null", "data"):
        m.append(("E3_grmf_lg1", lambda X, g, n, K: P.grmf(X, g, n, lam_g=1.0)))
    m.append(("E6_resid_on_lowrank", None))  # handled in the loop (needs the shared low-rank base)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--n-cells", type=int, nargs="*", default=[0], help="0 = all cells; else stratified subsample")
    ap.add_argument("--tag", default="")
    a = ap.parse_args(argv)
    seeds = a.seeds or ([100] if a.quick else DEV_SEEDS)
    if set(seeds) & CONFIRM_SEEDS:
        sys.exit("refusing: confirmation seeds are reserved for the single v2 confirmation run")
    n_nulls = 1 if a.quick else 3
    masks = ["MCAR"] if a.quick else ["MCAR", "MNAR"]
    adata_full = load_petrosius2023()
    names = list(adata_full.var_names)
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    curated = {n: build_prior(n, names) for n in ["corum", "complexportal"]}
    string = {n: build_prior(n, names) for n in ["string", "string_exp"]}
    rows = []
    t0 = time.time()
    for n_cells in a.n_cells:
      for kind in masks:
        for seed in seeds:
            if n_cells:
                rng = np.random.default_rng(seed)
                ct = adata_full.obs["cell_type"].values
                idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], n_cells // 4, replace=False)
                                              for c in sorted(set(ct))]))
                adata = adata_full[idx].copy()
            else:
                adata = adata_full
            X = np.asarray(adata.X, float)
            eligible = (~np.isnan(X)).mean(0) >= 0.5
            mask = make_mask(X, eligible, kind, seed)
            Xm = X.copy()
            Xm[mask] = np.nan
            truth = X[mask]
            _, cols = np.nonzero(mask)
            strat = {"all": np.ones(len(cols), bool), "in_complex": in_cx[cols], "not_in_complex": ~in_cx[cols]}

            def score(label, graph_kind, graph_name, filled):
                e = filled[mask] - truth
                rows.append({"n_cells": int(adata.n_obs), "mask": kind, "seed": seed, "method": label, "graph_kind": graph_kind,
                             "graph": graph_name,
                             **{f"rmse_{s}": float(np.sqrt(np.mean(e[sel] ** 2))) for s, sel in strat.items()}})

            K = P.loo_knn(Xm)
            score("knn_loo", "none", "-", P._fill(Xm, K))
            score("knn_scp_prep", "none", "-", knn_fill(from_log2_matrix(Xm, adata.obs_names, names)))
            graphs = []
            for n, g in curated.items():
                graphs.append(("curated", n, g))
                for i in range(n_nulls):
                    graphs.append(("null", f"{n}__null{i}", shuffled_null(g, i)))
                graphs.append(("data", f"data_matched_{n}", P.data_graph(Xm, names, g.number_of_edges())))
            for n, g in string.items():
                graphs.append(("string", n, g))
            dg = {n: g for k_, n, g in graphs if k_ == "data"}
            for n, g in curated.items():
                graphs.append(("union_curated", f"data+{n}", P.union_graph(dg[f"data_matched_{n}"], g)))
                graphs.append(("union_null", f"data+{n}__null0", P.union_graph(dg[f"data_matched_{n}"], shuffled_null(g, 0))))
            LR = P.grmf(Xm, None, names, lam_g=0.0, full=True)
            score("E3_lowrank_nograph", "data", "-", P._fill(Xm, LR))
            for gk, gn, g in graphs:
                for label, fn in methods_for(gk):
                    if label == "E3_grmf_lg1" and gk.startswith("union"):
                        continue
                    filled = P.residual_on_knn(Xm, g, names, K=LR) if fn is None else fn(Xm, g, names, K)
                    score(label, gk, gn, filled)
            log(f"n_cells={adata.n_obs} {kind} seed {seed} done ({time.time() - t0:.0f}s)")
    out = ROOT / "results" / "phase2" / "dev"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"dev_results{'_quick' if a.quick else ''}{a.tag}.json").write_text(
        json.dumps({"seeds": seeds, "masks": masks, "n_nulls": n_nulls, "rows": rows}, indent=1) + "\n")
    summarise(rows)


def summarise(rows):
    import pandas as pd

    df = pd.DataFrame(rows)
    df["graph_base"] = df["graph"].str.replace(r"__null\d+", "__null", regex=True)
    t = (df.groupby(["n_cells", "mask", "method", "graph_kind", "graph_base"])["rmse_in_complex"].mean()
           .unstack("mask").round(4).sort_values(list(df["mask"].unique())))
    print(t.to_string())
    return t


if __name__ == "__main__":
    main()
