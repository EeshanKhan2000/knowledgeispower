"""Single-use confirmation of H14 on the brunner2022 holdout (PREREGISTRATION_v7.md).

    python benchmarks/confirm_v7.py                -> results/confirm_v7/confirm_v7.json   (refuses to run twice)
    python benchmarks/confirm_v7.py --dry-run-dev  -> scratch output on a DEV dataset (specht2021, 2 seeds)
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import anndata as ad
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_bio import GRID, KAPPA, phys_graph, reference_datasets  # noqa: E402
from run import SIG_TOL, boot_rmse_diff, make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp import refpanel as R  # noqa: E402
from scp_graphfs_mcp import transfer as T  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    dry = "--dry-run-dev" in sys.argv
    if dry:
        from scp_graphfs_mcp.datasets import load_specht2021
        out_path = Path("/tmp/claude-0/-home-user-knowledgeispower/19f0adc1-0e52-561e-b422-c31fec9b93e5/scratchpad/confirm_v7_dryrun.json")
        seeds, per_type, exclude = [100, 101], 15, ("specht2021",)
        full = load_specht2021()
    else:
        out_path = ROOT / "results" / "confirm_v7" / "confirm_v7.json"
        if out_path.exists():
            sys.exit(f"refusing: {out_path} exists; the v7 confirmation is single-use")
        if subprocess.run(["git", "diff", "--quiet", "--", "src", "benchmarks"], cwd=ROOT).returncode != 0:
            sys.exit("refusing: uncommitted changes in src/ or benchmarks/")
        seeds, per_type, exclude = list(range(7000, 7010)), 6, ()
        full = ad.read_h5ad(ROOT / "data" / "datasets" / "brunner2022_holdout.h5ad")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    t0 = time.time()
    names = list(full.var_names)
    ds = reference_datasets()
    assert "brunner2022" not in ds
    Z = np.vstack([T.corpus_reference(names, exclude, ds), T.bulk_reference(names)])
    V, warm = T.fit_loadings(Z)
    nulls = [T.permute_rows(V, warm, s) for s in (0, 1)]
    nb = R.neighbours_from_graph(phys_graph(names), names)
    nb_null = R.permute_neighbours(nb, 0)
    Vk, uk = T.coldstart(*T.fit_loadings(Z, kg=nb, kappa=KAPPA), nb)
    Vn, un = T.coldstart(*T.fit_loadings(Z, kg=nb_null, kappa=KAPPA), nb_null)
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    ct = full.obs["cell_type"].values
    types = sorted(set(ct))
    out = {"code_commit": commit, "dataset": "specht2021 (DRY RUN)" if dry else "brunner2022", "seeds": seeds,
           "reference": {"datasets": ds, "shape": list(Z.shape), "warm_fraction": float(warm.mean())},
           "in_complex_fraction_of_proteins": float(in_cx.mean()), "masks": {}}
    for kind in ["MCAR", "MNAR"]:
        se, sels, wts = {}, [], []
        for seed in seeds:
            rng = np.random.default_rng(seed)
            idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], per_type, replace=False) for c in types]))
            X = np.asarray(full.X, float)[idx]
            eligible = (~np.isnan(X)).mean(0) >= 0.5
            mask = make_mask(X, eligible, kind, seed)
            Xm = X.copy()
            Xm[mask] = np.nan
            truth = X[mask]
            sels.append(in_cx[np.nonzero(mask)[1]])
            r2 = np.random.default_rng(seed + 7919)
            cand = np.argwhere(~np.isnan(Xm) & eligible[None, :])
            pick = cand[r2.choice(len(cand), max(1, int(0.1 * len(cand))), replace=False)]
            Xi = Xm.copy()
            Xi[pick[:, 0], pick[:, 1]] = np.nan
            ti = Xm[pick[:, 0], pick[:, 1]]
            pk = lambda M: M[pick[:, 0], pick[:, 1]]  # noqa: E731

            def stack(fulls, inners):
                g = GRID[len(fulls)]
                errs = [np.nanmean((sum(w * pk(p) for w, p in zip(ws, inners)) - ti) ** 2) for ws in g]
                ws = g[int(np.argmin(errs))]
                return sum(w * p for w, p in zip(ws, fulls)), list(ws)

            base, bi = P._fill(Xm, P.loo_knn(Xm)), P._fill(Xi, P.loo_knn(Xi))
            lr, lri = P.grmf(Xm, None, names, lam_g=0.0), P.grmf(Xi, None, names, lam_g=0.0)
            pj = lambda VV, uu: (T.project(Xm, VV, uu, base), T.project(Xi, VV, uu, bi))  # noqa: E731
            preds = {"knn": base, "stack_lowrank": stack([base, lr], [bi, lri])[0]}
            p0 = pj(V, warm)
            preds["stack3_plain"], w = stack([base, lr, p0[0]], [bi, lri, p0[1]])
            wts.append(w)
            for s, Vv in enumerate(nulls):
                pn = pj(Vv, warm)
                preds[f"stack3_plain@null{s}"] = stack([base, lr, pn[0]], [bi, lri, pn[1]])[0]
            pkg, pkn = pj(Vk, uk), pj(Vn, un)
            rr, rn = (R.rpr(Xm, nb, base=base), R.rpr(Xi, nb, base=bi)), (R.rpr(Xm, nb_null, base=base), R.rpr(Xi, nb_null, base=bi))
            preds["bim"] = stack([base, lr, pkg[0], rr[0]], [bi, lri, pkg[1], rr[1]])[0]
            preds["bim_null"] = stack([base, lr, pkn[0], rn[0]], [bi, lri, pkn[1], rn[1]])[0]
            for m, Y in preds.items():
                se.setdefault(m, []).append((Y[mask] - truth) ** 2)
            print(f"[{time.strftime('%H:%M:%S')}] {kind} seed {seed} ({time.time() - t0:.0f}s)", flush=True)
        SE = {m: np.concatenate(v) for m, v in se.items()}
        sel = np.concatenate(sels)
        res = {"rmse_in_complex": {m: float(np.sqrt(v[sel].mean())) for m, v in SE.items()},
               "rmse_all": {m: float(np.sqrt(v.mean())) for m, v in SE.items()},
               "n_masked_in_complex": int(sel.sum()), "stack3_weights": wts, "comparisons": []}

        def cmp(a, refs, label, role, endpoint):
            f = (lambda v: v[sel]) if endpoint == "in_complex" else (lambda v: v)
            c = boot_rmse_diff(f(SE[a]), [f(SE[r]) for r in refs], 1000, seed=17)
            ref = float(np.mean([np.sqrt(f(SE[r]).mean()) for r in refs]))
            pct = 100 * c["delta_rmse"] / ref
            res["comparisons"].append({"method": a, "vs": label, "role": role, "endpoint": endpoint, **c,
                                       "pct_of_ref_rmse": pct, "pass": bool(c["ci95"][1] < -SIG_TOL and pct <= -1.0)})

        nl = ["stack3_plain@null0", "stack3_plain@null1"]
        for ep, role in (("in_complex", "primary"), ("all", "secondary")):
            cmp("stack3_plain", ["knn"], "knn", role, ep)
            cmp("stack3_plain", ["stack_lowrank"], "stack_lowrank", role, ep)
            cmp("stack3_plain", nl, "own_null_mean", role, ep)
        cmp("bim", ["stack3_plain"], "stack3_plain", "secondary", "in_complex")
        cmp("bim", ["bim_null"], "bim_null", "secondary", "in_complex")
        out["masks"][kind] = res
    prim = [c["pass"] for k in out["masks"].values() for c in k["comparisons"] if c["role"] == "primary"]
    out["H14_confirmed"] = bool(all(prim))
    out["primary_passes"] = f"{sum(prim)}/{len(prim)}"
    out["runtime_seconds"] = round(time.time() - t0, 1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ["H14_confirmed", "primary_passes", "runtime_seconds"]}))
    for k, v in out["masks"].items():
        for c in v["comparisons"]:
            print(k, c["role"], c["endpoint"], c["method"], "vs", c["vs"], f"{c['pct_of_ref_rmse']:+.2f}%",
                  [round(x, 4) for x in c["ci95"]], "PASS" if c["pass"] else "fail")


if __name__ == "__main__":
    main()
