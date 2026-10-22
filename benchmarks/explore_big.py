"""Amendment-11 DEV: bigger external reference + three-way stack (kNN, low-rank, reference projection).

    python benchmarks/explore_big.py     -> results/phase8/dev/dev_big.json (+ selection, corpus list)

Dev seeds 100-102 only. Holdouts are never loaded; each target is excluded from its own reference.
"""

from __future__ import annotations

import itertools
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_reps import SEEDS, TARGETS  # noqa: E402
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp import transfer as T  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase8" / "dev"
CACHE = ROOT / "data" / "cache" / "transfer"
GRID2 = (0.0, 0.25, 0.5, 0.75, 1.0)
GRID3 = [w for w in itertools.product(GRID2, repeat=3) if abs(sum(w) - 1) < 1e-9]


def precompute(tname: str, datasets: list[str]):
    f = CACHE / f"{tname}_big.npz"
    if f.exists():
        return
    names = list(TARGETS[tname][0]().var_names)
    Z = np.vstack([T.corpus_reference(names, (tname,), datasets), T.bulk_reference(names)])
    V, warm = T.fit_loadings(Z)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, V=V, warm=warm, n_ref=Z.shape[0])
    print(f"[{time.strftime('%H:%M:%S')}] {tname}: big ref {Z.shape}, warm {warm.mean():.3f}", flush=True)


def run_config(args):
    tname, n_cells, kind, seed = args
    full = TARGETS[tname][0]()
    names = list(full.var_names)
    B = np.load(CACHE / f"{tname}_big.npz")
    A10 = np.load(CACHE / f"{tname}.npz")
    ct = full.obs["cell_type"].values
    types = sorted(set(ct))
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
    rows = []

    def rec(method, Y, w=None):
        rows.append({"target": tname, "n_cells": int(len(idx)), "mask": kind, "seed": seed, "method": method,
                     "rmse_all": float(np.sqrt(np.mean((Y[mask] - truth) ** 2))), "weights": w})

    rng = np.random.default_rng(seed + 7919)
    cand = np.argwhere(~np.isnan(Xm) & eligible[None, :])
    pick = cand[rng.choice(len(cand), max(1, int(0.1 * len(cand))), replace=False)]
    Xi = Xm.copy()
    Xi[pick[:, 0], pick[:, 1]] = np.nan
    ti = Xm[pick[:, 0], pick[:, 1]]
    base = P._fill(Xm, P.loo_knn(Xm))
    bi = P._fill(Xi, P.loo_knn(Xi))
    lr, lri = P.grmf(Xm, None, names, lam_g=0.0), P.grmf(Xi, None, names, lam_g=0.0)
    pk = lambda M: M[pick[:, 0], pick[:, 1]]  # noqa: E731

    def stack(parts_full, parts_inner, grid):
        errs = [np.nanmean((sum(w * pk(p) for w, p in zip(ws, parts_inner)) - ti) ** 2) for ws in grid]
        ws = grid[int(np.argmin(errs))]
        return sum(w * p for w, p in zip(ws, parts_full)), list(ws)

    g2 = [(w, 1 - w) for w in GRID2]
    rec("knn", base)
    rec("lowrank", lr)
    rec("stack_lowrank", *stack([base, lr], [bi, lri], g2))
    Va, wa = A10["V_all"], A10["warm_all"]
    ta, tai = T.project(Xm, Va, wa, base), T.project(Xi, Va, wa, bi)
    rec("stack2_all", *stack([base, ta], [bi, tai], g2))
    V, warm = B["V"], B["warm"]
    variants = {"": V, "@null0": T.permute_rows(V, warm, 0), "@null1": T.permute_rows(V, warm, 1)}
    for sfx, Vv in variants.items():
        tb, tbi = T.project(Xm, Vv, warm, base), T.project(Xi, Vv, warm, bi)
        rec(f"refmf_big{sfx}", tb)
        rec(f"stack2_big{sfx}", *stack([base, tb], [bi, tbi], g2))
        rec(f"stack3_big{sfx}", *stack([base, lr, tb], [bi, lri, tbi], GRID3))
    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} done", flush=True)
    return rows


def select(rows):
    import pandas as pd

    df = pd.DataFrame(rows)
    df = df[df.n_cells <= 30]
    m = df.groupby(["target", "mask", "method"])["rmse_all"].mean()
    out = []
    for c in ["refmf_big", "stack2_big", "stack3_big"]:
        wins, rel = {}, []
        for (t, k) in sorted({(a, b) for a, b in zip(df.target, df["mask"])}):
            v = m[(t, k, c)]
            bars = {b: m[(t, k, b)] for b in ("knn", "lowrank", "stack_lowrank", "stack2_all")}
            bars.update({f"null{s}": m[(t, k, f"{c}@null{s}")] for s in (0, 1)})
            wins[(t, k)] = all(v <= 0.99 * b for b in bars.values())
            rel.append(v / bars["knn"])
        by_t = {t: all(wins.get((t, k), False) for k in ("MCAR", "MNAR")) for t in {a for a, _ in wins}}
        out.append({"method": c, "targets_won_both_masks": sum(by_t.values()), "qualifies": sum(by_t.values()) >= 2,
                    "mean_rel_to_knn": float(np.mean(rel)), "per_target": by_t})
    out.sort(key=lambda d: (not d["qualifies"], d["mean_rel_to_knn"]))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    datasets = T.extended_corpus()
    (OUT / "corpus_used.json").write_text(json.dumps(datasets, indent=1) + "\n")
    for t in TARGETS:
        precompute(t, datasets)
    jobs = [(t, n, k, s) for t, (_, regimes) in TARGETS.items() for n in regimes for k in ("MCAR", "MNAR") for s in SEEDS]
    with ProcessPoolExecutor(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4) as ex:
        rows = [r for rs in ex.map(run_config, jobs) for r in rs]
    (OUT / "dev_big.json").write_text(json.dumps({"seeds": SEEDS, "corpus": datasets, "rows": rows}, indent=1) + "\n")
    sel = select(rows)
    (OUT / "dev_big_selection.json").write_text(json.dumps(sel, indent=1) + "\n")
    for d in sel:
        print(d)


if __name__ == "__main__":
    main()
