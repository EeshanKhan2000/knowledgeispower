"""Single confirmation run for PREREGISTRATION_v2.md (seeds 1000-1004). Refuses to run twice.

    python benchmarks/confirm_v2.py   -> results/phase2/confirm/confirm_v2.json
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
from scp_graphfs_mcp.datasets import from_log2_matrix, load_petrosius2023  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.methods import knn_fill  # noqa: E402
from scp_graphfs_mcp.priors import build_prior, shuffled_null  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [1000, 1001, 1002, 1003, 1004]
OUT = ROOT / "results" / "phase2" / "confirm" / "confirm_v2.json"


def main():
    if OUT.exists():
        sys.exit(f"refusing: {OUT} exists; the confirmation masks are used once")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.run(["git", "diff", "--quiet", "--", "src", "benchmarks"], cwd=ROOT).returncode != 0
    if dirty:
        sys.exit("refusing: uncommitted changes in src/ or benchmarks/; commit first so the run is traceable")
    t0 = time.time()
    adata = load_petrosius2023()
    names = list(adata.var_names)
    X = np.asarray(adata.X, float)
    eligible = (~np.isnan(X)).mean(0) >= 0.5
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    G = {n: build_prior(n, names) for n in ["corum", "complexportal", "string", "string_exp"]}
    nulls = {n: [shuffled_null(G[n], s) for s in range(10)] for n in ["corum", "complexportal"]}
    out = {"code_commit": commit, "seeds": SEEDS, "masks": {}}
    for kind in ["MCAR", "MNAR"]:
        se: dict[str, list] = {}
        incx = []
        for seed in SEEDS:
            mask = make_mask(X, eligible, kind, seed)
            Xm = X.copy()
            Xm[mask] = np.nan
            truth = X[mask]
            _, cols = np.nonzero(mask)
            incx.append(in_cx[cols])
            preds = {}
            preds["knn"] = knn_fill(from_log2_matrix(Xm, adata.obs_names, names))
            LR = P.grmf(Xm, None, names, lam_g=0.0, full=True)
            preds["lowrank_nograph"] = P._fill(Xm, LR)
            # primary
            preds["E3_corum"] = P.grmf(Xm, G["corum"], names, lam_g=1.0)
            for i, h in enumerate(nulls["corum"]):
                preds[f"E3_corum__null{i}"] = P.grmf(Xm, h, names, lam_g=1.0)
            dg_c = P.data_graph(Xm, names, G["corum"].number_of_edges())
            preds["E3_data_matched_corum"] = P.grmf(Xm, dg_c, names, lam_g=1.0)
            # secondary
            for n in ["complexportal", "string", "string_exp"]:
                preds[f"E3_{n}"] = P.grmf(Xm, G[n], names, lam_g=1.0)
            K = P.loo_knn(Xm)
            dg_p = P.data_graph(Xm, names, G["complexportal"].number_of_edges())
            preds["E6_complexportal"] = P.residual_on_knn(Xm, G["complexportal"], names, K=LR)
            preds["E6_data_matched_complexportal"] = P.residual_on_knn(Xm, dg_p, names, K=LR)
            preds["E1E4_complexportal"] = P.residual_on_knn(Xm, G["complexportal"], names, K=K, gate=1.0)
            preds["E1E4_data_matched_complexportal"] = P.residual_on_knn(Xm, dg_p, names, K=K, gate=1.0)
            for i, h in enumerate(nulls["complexportal"]):
                preds[f"E6_complexportal__null{i}"] = P.residual_on_knn(Xm, h, names, K=LR)
                preds[f"E1E4_complexportal__null{i}"] = P.residual_on_knn(Xm, h, names, K=K, gate=1.0)
            for m, Y in preds.items():
                se.setdefault(m, []).append((Y[mask] - truth) ** 2)
            print(f"[{time.strftime('%H:%M:%S')}] {kind} seed {seed} ({time.time() - t0:.0f}s)", flush=True)
        SE = {m: np.concatenate(v) for m, v in se.items()}
        sel = np.concatenate(incx)
        rmse = {m: {"in_complex": float(np.sqrt(v[sel].mean())), "not_in_complex": float(np.sqrt(v[~sel].mean())),
                    "all": float(np.sqrt(v.mean()))} for m, v in SE.items()}

        def cmp(a, refs, label, role):
            c = boot_rmse_diff(SE[a][sel], [SE[r][sel] for r in refs], 1000, seed=17)
            return {"method": a, "vs": label, "role": role, **c, "pass": c["ci95"][1] < -SIG_TOL}

        n_c = [f"E3_corum__null{i}" for i in range(10)]
        n_p6 = [f"E6_complexportal__null{i}" for i in range(10)]
        n_p14 = [f"E1E4_complexportal__null{i}" for i in range(10)]
        comps = [cmp("E3_corum", ["knn"], "knn", "primary"),
                 cmp("E3_corum", ["lowrank_nograph"], "lowrank_nograph", "primary"),
                 cmp("E3_corum", n_c, "own_null_mean", "primary"),
                 cmp("E3_corum", ["E3_data_matched_corum"], "data_graph", "primary"),
                 cmp("E6_complexportal", ["lowrank_nograph"], "lowrank_nograph", "secondary"),
                 cmp("E6_complexportal", n_p6, "own_null_mean", "secondary"),
                 cmp("E6_complexportal", ["E6_data_matched_complexportal"], "data_graph", "secondary"),
                 cmp("E1E4_complexportal", ["knn"], "knn", "secondary"),
                 cmp("E1E4_complexportal", n_p14, "own_null_mean", "secondary"),
                 cmp("E1E4_complexportal", ["E1E4_data_matched_complexportal"], "data_graph", "secondary"),
                 cmp("E1E4_complexportal", ["lowrank_nograph"], "lowrank_nograph", "secondary")]
        out["masks"][kind] = {"rmse": rmse, "comparisons": comps}
    prim = [c["pass"] for k in out["masks"].values() for c in k["comparisons"] if c["role"] == "primary"]
    out["primary_confirmed"] = bool(all(prim))
    out["primary_passes"] = f"{sum(prim)}/{len(prim)}"
    out["runtime_seconds"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ["primary_confirmed", "primary_passes"]}))
    for k, v in out["masks"].items():
        for c in v["comparisons"]:
            print(k, c["role"], c["method"], "vs", c["vs"], f"{c['delta_rmse']:+.4f}", [round(x, 4) for x in c["ci95"]],
                  "PASS" if c["pass"] else "fail")


if __name__ == "__main__":
    main()
