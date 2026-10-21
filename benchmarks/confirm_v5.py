"""Single low-data-regime confirmation for PREREGISTRATION_v5.md (SCoPE2, subsample seeds 4000-4009).

    python benchmarks/confirm_v5.py   -> results/phase3/confirm_v5.json   (refuses to run twice)
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
from scp_graphfs_mcp.datasets import load_specht2021  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.priors import build_prior, shuffled_null  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEEDS = list(range(4000, 4010))
REGIMES = [30, 60]
OUT = ROOT / "results" / "phase3" / "confirm_v5.json"


def main():
    if OUT.exists():
        sys.exit(f"refusing: {OUT} exists; the v4 confirmation is single-use")
    if subprocess.run(["git", "diff", "--quiet", "--", "src", "benchmarks"], cwd=ROOT).returncode != 0:
        sys.exit("refusing: uncommitted changes in src/ or benchmarks/")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    t0 = time.time()
    full = load_specht2021()
    names = list(full.var_names)
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    G = {n: build_prior(n, names) for n in ["complexportal", "corum"]}
    nulls = {n: [shuffled_null(G[n], s) for s in range(5)] for n in G}
    ct = full.obs["cell_type"].values
    types = sorted(set(ct))
    out = {"code_commit": commit, "dataset": "specht2021", "seeds": SEEDS, "regimes": {}}
    for n_cells in REGIMES:
        out["regimes"][str(n_cells)] = {}
        for kind in ["MCAR", "MNAR"]:
            se: dict[str, list] = {}
            incx = []
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], n_cells // len(types), replace=False)
                                              for c in types]))
                X = np.asarray(full.X, float)[idx]
                eligible = (~np.isnan(X)).mean(0) >= 0.5
                mask = make_mask(X, eligible, kind, seed)
                Xm = X.copy()
                Xm[mask] = np.nan
                truth = X[mask]
                _, cols = np.nonzero(mask)
                incx.append(in_cx[cols])
                K = P.loo_knn(Xm)
                preds = {"knn": P._fill(Xm, K)}
                for cur in ["complexportal", "corum"]:
                    dg = P.data_graph(Xm, names, G[cur].number_of_edges())
                    preds[f"data_{cur}"] = P.residual_on_knn(Xm, dg, names, K=K, gate=1.0)
                    preds[f"{cur}_alone"] = P.residual_on_knn(Xm, G[cur], names, K=K, gate=1.0)
                    for i, h in enumerate(nulls[cur]):
                        preds[f"{cur}_alone__null{i}"] = P.residual_on_knn(Xm, h, names, K=K, gate=1.0)
                for m, Y in preds.items():
                    se.setdefault(m, []).append((Y[mask] - truth) ** 2)
                print(f"[{time.strftime('%H:%M:%S')}] n={n_cells} {kind} seed {seed} ({time.time() - t0:.0f}s)", flush=True)
            SE = {m: np.concatenate(v) for m, v in se.items()}
            sel = np.concatenate(incx)
            rmse = {m: {"in_complex": float(np.sqrt(v[sel].mean())), "not_in_complex": float(np.sqrt(v[~sel].mean()))}
                    for m, v in SE.items()}
            role = "primary" if n_cells == 30 else "secondary"

            def cmp(a, refs, label, r):
                c = boot_rmse_diff(SE[a][sel], [SE[x][sel] for x in refs], 1000, seed=17)
                ref = float(np.mean([np.sqrt(SE[x][sel].mean()) for x in refs]))
                pct = 100 * c["delta_rmse"] / ref
                return {"method": a, "vs": label, "role": r, **c, "pct_of_ref_rmse": pct,
                        "pass": bool(c["ci95"][1] < -SIG_TOL and pct <= -1.0)}  # CI excludes 0 AND >= 1% (SESOI)

            comps = []
            for cur in ["complexportal", "corum"]:
                r = role if cur == "complexportal" else "secondary"
                nl = [f"{cur}_alone__null{i}" for i in range(5)]
                comps += [cmp(f"{cur}_alone", [f"data_{cur}"], "data_alone", r),
                          cmp(f"{cur}_alone", nl, "own_null_mean", r),
                          cmp(f"{cur}_alone", ["knn"], "knn", "secondary"),
                          cmp(f"data_{cur}", ["knn"], "knn", "secondary")]
            out["regimes"][str(n_cells)][kind] = {"rmse": rmse, "comparisons": comps,
                                                  "n_masked_in_complex": int(sel.sum())}
    prim = [c["pass"] for reg in out["regimes"].values() for k in reg.values()
            for c in k["comparisons"] if c["role"] == "primary"]
    out["primary_confirmed"] = bool(all(prim))
    out["primary_passes"] = f"{sum(prim)}/{len(prim)}"
    out["runtime_seconds"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ["primary_confirmed", "primary_passes", "runtime_seconds"]}))
    for n, reg in out["regimes"].items():
        for k, v in reg.items():
            for c in v["comparisons"]:
                print(n, k, c["role"], c["method"], "vs", c["vs"], f"{c['delta_rmse']:+.4f}",
                      [round(x, 4) for x in c["ci95"]], f"{c['pct_of_ref_rmse']:+.2f}%", "PASS" if c["pass"] else "fail")


if __name__ == "__main__":
    main()
