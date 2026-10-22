"""Single-use confirmation on the khan2023 holdout (PREREGISTRATION_v6.md; Amendments 9-11).

    python benchmarks/confirm_v6.py <method>   -> results/confirm_v6/confirm_v6.json   (refuses to run twice)

<method> must be the Amendment-11 qualifier named in PREREGISTRATION_v6.md (refmf_big | stack2_big | stack3_big).
Reference = the full extended corpus (khan2023 is never in it) + CCLE + ProteomeHD, aligned to khan2023's proteins.
Seeds 6000-6009, 30-cell subsamples stratified by day, MCAR and MNAR. Pass = for every comparator, the 95% paired-
bootstrap CI of RMSE(method) - RMSE(comparator) is entirely below 0 AND the point estimate is <= -1% (SESOI).
"""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import SIG_TOL, boot_rmse_diff, make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp import transfer as T  # noqa: E402
from scp_graphfs_mcp.datasets import load_khan2023  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEEDS = list(range(6000, 6010))
N_CELLS = 30
OUT = ROOT / "results" / "confirm_v6" / "confirm_v6.json"
GRID2 = (0.0, 0.25, 0.5, 0.75, 1.0)
GRID3 = [w for w in itertools.product(GRID2, repeat=3) if abs(sum(w) - 1) < 1e-9]


def main():
    method = sys.argv[1]
    assert method in ("refmf_big", "stack2_big", "stack3_big")
    prereg = (ROOT / "benchmarks" / "PREREGISTRATION_v6.md").read_text()
    if f"`{method}`" not in prereg:
        sys.exit(f"refusing: {method} is not the method named in PREREGISTRATION_v6.md")
    if OUT.exists():
        sys.exit(f"refusing: {OUT} exists; the v6 confirmation is single-use")
    if subprocess.run(["git", "diff", "--quiet", "--", "src", "benchmarks"], cwd=ROOT).returncode != 0:
        sys.exit("refusing: uncommitted changes in src/ or benchmarks/")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    t0 = time.time()
    full = load_khan2023()
    names = list(full.var_names)
    datasets = T.extended_corpus()
    Z = np.vstack([T.corpus_reference(names, (), datasets), T.bulk_reference(names)])
    V, warm = T.fit_loadings(Z)
    nulls = [T.permute_rows(V, warm, s) for s in (0, 1)]
    Za = np.vstack([T.corpus_reference(names, ()), T.bulk_reference(names)])  # Amendment-10 reference (baseline)
    Va, warm_a = T.fit_loadings(Za)
    ct = full.obs["cell_type"].values
    types = sorted(set(ct))
    out = {"code_commit": commit, "dataset": "khan2023", "method": method, "seeds": SEEDS, "n_cells": N_CELLS,
           "reference": {"datasets": datasets, "shape": list(Z.shape), "warm_fraction": float(warm.mean())}, "masks": {}}
    for kind in ["MCAR", "MNAR"]:
        se: dict[str, list] = {}
        weights = []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], N_CELLS // len(types), replace=False)
                                          for c in types]))
            X = np.asarray(full.X, float)[idx]
            eligible = (~np.isnan(X)).mean(0) >= 0.5
            mask = make_mask(X, eligible, kind, seed)
            Xm = X.copy()
            Xm[mask] = np.nan
            truth = X[mask]
            r2 = np.random.default_rng(seed + 7919)
            cand = np.argwhere(~np.isnan(Xm) & eligible[None, :])
            pick = cand[r2.choice(len(cand), max(1, int(0.1 * len(cand))), replace=False)]
            Xi = Xm.copy()
            Xi[pick[:, 0], pick[:, 1]] = np.nan
            ti = Xm[pick[:, 0], pick[:, 1]]
            pk = lambda M: M[pick[:, 0], pick[:, 1]]  # noqa: E731
            base, bi = P._fill(Xm, P.loo_knn(Xm)), P._fill(Xi, P.loo_knn(Xi))
            lr, lri = P.grmf(Xm, None, names, lam_g=0.0), P.grmf(Xi, None, names, lam_g=0.0)

            def stack(full_parts, inner_parts, grid):
                errs = [np.nanmean((sum(w * pk(p) for w, p in zip(ws, inner_parts)) - ti) ** 2) for ws in grid]
                ws = grid[int(np.argmin(errs))]
                return sum(w * p for w, p in zip(ws, full_parts)), list(ws)

            g2 = [(w, 1 - w) for w in GRID2]
            preds = {"knn": base, "lowrank": lr, "stack_lowrank": stack([base, lr], [bi, lri], g2)[0],
                     "stack2_all": stack([base, T.project(Xm, Va, warm_a, base)], [bi, T.project(Xi, Va, warm_a, bi)], g2)[0]}

            def candidate(Vv):
                tb, tbi = T.project(Xm, Vv, warm, base), T.project(Xi, Vv, warm, bi)
                if method == "refmf_big":
                    return tb, None
                if method == "stack2_big":
                    return stack([base, tb], [bi, tbi], g2)
                return stack([base, lr, tb], [bi, lri, tbi], GRID3)

            preds[method], w = candidate(V)
            weights.append(w)
            for s, Vn in enumerate(nulls):
                preds[f"{method}@null{s}"] = candidate(Vn)[0]
            for m, Y in preds.items():
                se.setdefault(m, []).append((Y[mask] - truth) ** 2)
            print(f"[{time.strftime('%H:%M:%S')}] {kind} seed {seed} ({time.time() - t0:.0f}s)", flush=True)
        SE = {m: np.concatenate(v) for m, v in se.items()}
        rmse = {m: float(np.sqrt(v.mean())) for m, v in SE.items()}
        comps = []
        for label, refs in [("knn", ["knn"]), ("lowrank", ["lowrank"]), ("stack_lowrank", ["stack_lowrank"]),
                            ("stack2_all", ["stack2_all"]),
                            ("own_null_mean", [f"{method}@null0", f"{method}@null1"])]:
            c = boot_rmse_diff(SE[method], [SE[r] for r in refs], 1000, seed=17)
            ref = float(np.mean([rmse[r] for r in refs]))
            pct = 100 * c["delta_rmse"] / ref
            comps.append({"vs": label, **c, "pct_of_ref_rmse": pct,
                          "pass": bool(c["ci95"][1] < -SIG_TOL and pct <= -1.0)})
        out["masks"][kind] = {"rmse": rmse, "comparisons": comps, "stack_weights": weights}
    passes = [c["pass"] for k in out["masks"].values() for c in k["comparisons"]]
    out["confirmed"] = bool(all(passes))
    out["passes"] = f"{sum(passes)}/{len(passes)}"
    out["runtime_seconds"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ["confirmed", "passes", "runtime_seconds"]}))
    for k, v in out["masks"].items():
        for c in v["comparisons"]:
            print(k, method, "vs", c["vs"], f"{c['delta_rmse']:+.4f}", [round(x, 4) for x in c["ci95"]],
                  f"{c['pct_of_ref_rmse']:+.2f}%", "PASS" if c["pass"] else "fail")


if __name__ == "__main__":
    main()
