"""Single independent-dataset confirmation for PREREGISTRATION_v3.md (Leduc 2022, seeds 2000-2004).

    python benchmarks/confirm_v3.py   -> results/phase3/confirm_v3.json   (refuses to run twice)
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import SIG_TOL, boot_rmse_diff, make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.datasets import from_log2_matrix, load_leduc2022  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.methods import knn_fill  # noqa: E402
from scp_graphfs_mcp.priors import build_prior, shuffled_null  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [2000, 2001, 2002, 2003, 2004]
OUT = ROOT / "results" / "phase3" / "confirm_v3.json"


def main():
    if OUT.exists():
        sys.exit(f"refusing: {OUT} exists; the v3 confirmation is single-use")
    if subprocess.run(["git", "diff", "--quiet", "--", "src", "benchmarks"], cwd=ROOT).returncode != 0:
        sys.exit("refusing: uncommitted changes in src/ or benchmarks/")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    t0 = time.time()
    adata = load_leduc2022()
    names = list(adata.var_names)
    X = np.asarray(adata.X, float)
    eligible = (~np.isnan(X)).mean(0) >= 0.5
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    G = {n: build_prior(n, names) for n in ["complexportal", "corum", "string"]}
    cp_nulls = [shuffled_null(G["complexportal"], s) for s in range(10)]
    out = {"code_commit": commit, "dataset": "leduc2022", "seeds": SEEDS, "n_cells": adata.n_obs,
           "n_proteins": adata.n_vars, "n_eligible": int(eligible.sum()), "n_in_complex": int(in_cx.sum()),
           "coverage": {n: {k: v for k, v in g.graph["coverage"].items() if k != "unmapped"} for n, g in G.items()},
           "masks": {}}
    for kind in ["MCAR", "MNAR"]:
        se: dict[str, list] = {}
        incx = []
        betas = []
        for seed in SEEDS:
            mask = make_mask(X, eligible, kind, seed)
            Xm = X.copy()
            Xm[mask] = np.nan
            truth = X[mask]
            _, cols = np.nonzero(mask)
            incx.append(in_cx[cols])
            base = P.grmf(Xm, None, names, lam_g=0.0, full=True)
            preds = {"lowrank_nograph": P._fill(Xm, base),
                     "knn": knn_fill(from_log2_matrix(Xm, adata.obs_names, names))}
            e6, parts = P.residual_on_knn(Xm, G["complexportal"], names, K=base, return_parts=True)
            preds["E6_complexportal"] = e6
            betas.append(parts["beta"])
            for i, h in enumerate(cp_nulls):
                preds[f"E6_complexportal__null{i}"] = P.residual_on_knn(Xm, h, names, K=base)
            dg = P.data_graph(Xm, names, G["complexportal"].number_of_edges())
            preds["E6_data_matched_complexportal"] = P.residual_on_knn(Xm, dg, names, K=base)
            # secondary
            for n in ["corum", "string"]:
                preds[f"E6_{n}"] = P.residual_on_knn(Xm, G[n], names, K=base)
            for n in ["corum", "complexportal", "string"]:
                preds[f"E3_{n}"] = P.grmf(Xm, G[n], names, lam_g=1.0)
            for m, Y in preds.items():
                se.setdefault(m, []).append((Y[mask] - truth) ** 2)
            print(f"[{time.strftime('%H:%M:%S')}] {kind} seed {seed} ({time.time() - t0:.0f}s)", flush=True)
        SE = {m: np.concatenate(v) for m, v in se.items()}
        sel = np.concatenate(incx)
        rmse = {m: {"in_complex": float(np.sqrt(v[sel].mean())), "not_in_complex": float(np.sqrt(v[~sel].mean())),
                    "all": float(np.sqrt(v.mean()))} for m, v in SE.items()}

        def cmp(a, refs, label, role):
            c = boot_rmse_diff(SE[a][sel], [SE[r][sel] for r in refs], 1000, seed=17)
            return {"method": a, "vs": label, "role": role, **c, "pass": c["ci95"][1] < -SIG_TOL,
                    "pct_of_ref_rmse": 100 * c["delta_rmse"] / float(np.mean([np.sqrt(SE[r][sel].mean()) for r in refs]))}

        nulls = [f"E6_complexportal__null{i}" for i in range(10)]
        comps = [cmp("E6_complexportal", ["lowrank_nograph"], "lowrank_nograph", "primary"),
                 cmp("E6_complexportal", nulls, "own_null_mean", "primary"),
                 cmp("E6_complexportal", ["E6_data_matched_complexportal"], "data_graph", "primary"),
                 cmp("E6_complexportal", ["knn"], "knn", "primary"),
                 cmp("E6_corum", ["lowrank_nograph"], "lowrank_nograph", "secondary"),
                 cmp("E6_string", ["lowrank_nograph"], "lowrank_nograph", "secondary"),
                 cmp("E3_corum", ["lowrank_nograph"], "lowrank_nograph", "secondary"),
                 cmp("E3_complexportal", ["lowrank_nograph"], "lowrank_nograph", "secondary"),
                 cmp("E3_string", ["lowrank_nograph"], "lowrank_nograph", "secondary")]
        out["masks"][kind] = {"rmse": rmse, "comparisons": comps, "beta_by_seed": betas,
                              "n_masked_in_complex": int(sel.sum())}
    prim = [c["pass"] for k in out["masks"].values() for c in k["comparisons"] if c["role"] == "primary"]
    out["primary_confirmed"] = bool(all(prim))
    out["primary_passes"] = f"{sum(prim)}/{len(prim)}"
    out["runtime_seconds"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ["primary_confirmed", "primary_passes", "runtime_seconds"]}))
    for k, v in out["masks"].items():
        for c in v["comparisons"]:
            print(k, c["role"], c["method"], "vs", c["vs"], f"{c['delta_rmse']:+.4f}",
                  [round(x, 4) for x in c["ci95"]], f"{c['pct_of_ref_rmse']:+.2f}%", "PASS" if c["pass"] else "fail")


if __name__ == "__main__":
    main()
