"""Amendment-10 DEV: transfer from external references (reference-projection MF, KG cold-start, reference donors).

    python benchmarks/explore_transfer.py     -> results/phase7/dev/dev_transfer.json (+ selection)

Dev seeds 100-102 only. The holdouts are never loaded; each target is excluded from its own reference.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_reps import SEEDS, TARGETS, build_reps  # noqa: E402
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp import refpanel as R  # noqa: E402
from scp_graphfs_mcp import transfer as T  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase7" / "dev"
CACHE = ROOT / "data" / "cache" / "transfer"


def precompute(tname: str):
    f = CACHE / f"{tname}.npz"
    if f.exists():
        return
    names = list(TARGETS[tname][0]().var_names)
    reps, _ = build_reps(tname, names)
    nb = reps["union_curated"]["rpr"]
    nb_null = R.permute_neighbours(nb, 0)
    Zc = T.corpus_reference(names, (tname,))
    Za = np.vstack([Zc, T.bulk_reference(names)])
    out = {}
    for ref, Z in (("corpus", Zc), ("all", Za)):
        V, warm = T.fit_loadings(Z)
        Vk, uk = T.coldstart(V, warm, nb)
        Vn, un = T.coldstart(V, warm, nb_null)
        out.update({f"V_{ref}": V, f"warm_{ref}": warm, f"Vkg_{ref}": Vk, f"ukg_{ref}": uk,
                    f"Vkgnull_{ref}": Vn, f"ukgnull_{ref}": un})
        print(f"[{time.strftime('%H:%M:%S')}] {tname} {ref}: ref {Z.shape}, warm {warm.mean():.3f}, "
              f"usable after KG cold-start {uk.mean():.3f}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **out)


def run_config(args):
    tname, n_cells, kind, seed = args
    full = TARGETS[tname][0]()
    names = list(full.var_names)
    C = dict(np.load(CACHE / f"{tname}.npz"))
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
                     "rmse_all": float(np.sqrt(np.mean((Y[mask] - truth) ** 2))), "stack_w": w})

    rng = np.random.default_rng(seed + 7919)
    cand = np.argwhere(~np.isnan(Xm) & eligible[None, :])
    pick = cand[rng.choice(len(cand), max(1, int(0.1 * len(cand))), replace=False)]
    Xi = Xm.copy()
    Xi[pick[:, 0], pick[:, 1]] = np.nan
    ti = Xm[pick[:, 0], pick[:, 1]]
    base = P._fill(Xm, P.loo_knn(Xm))
    bi = P._fill(Xi, P.loo_knn(Xi))
    grid = (0.0, 0.25, 0.5, 0.75, 1.0)

    def both(name, make):
        rec(name, make(Xm, base))
        oi = make(Xi, bi)
        a, b = bi[pick[:, 0], pick[:, 1]], oi[pick[:, 0], pick[:, 1]]
        w = grid[int(np.argmin([np.nanmean((w * a + (1 - w) * b - ti) ** 2) for w in grid]))]
        rec(f"stack_{name}", w * base + (1 - w) * make(Xm, base), w)

    rec("knn", base)
    rec("lowrank", P.grmf(Xm, None, names, lam_g=0.0))
    both("lowrank_s", lambda A, b: P.grmf(A, None, names, lam_g=0.0))
    for ref in ("corpus", "all"):
        V, warm = C[f"V_{ref}"], C[f"warm_{ref}"]
        both(f"refmf_{ref}", lambda A, b, V=V, warm=warm: T.project(A, V, warm, b))
        for s in (0, 1):
            Vp = T.permute_rows(V, warm, s)
            both(f"refmf_{ref}@null{s}", lambda A, b, Vp=Vp, warm=warm: T.project(A, Vp, warm, b))
        both(f"refmf_{ref}_kg", lambda A, b, ref=ref: T.project(A, C[f"Vkg_{ref}"], C[f"ukg_{ref}"], b))
        both(f"refmf_{ref}_kg@null0", lambda A, b, ref=ref: T.project(A, C[f"Vkgnull_{ref}"], C[f"ukgnull_{ref}"], b))
    Zc = T.corpus_reference(names, (tname,))
    both("donor_corpus", lambda A, b: T.donor_knn(A, Zc, b))
    Zp = Zc[:, np.random.default_rng(0).permutation(Zc.shape[1])]
    both("donor_corpus@null0", lambda A, b: T.donor_knn(A, Zp, b))
    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} done", flush=True)
    return rows


def select(rows):
    import pandas as pd

    df = pd.DataFrame(rows)
    df = df[df.n_cells <= 30]
    m = df.groupby(["target", "mask", "method"])["rmse_all"].mean()
    cands = sorted({x for x in df.method if "@" not in x and x not in ("knn", "lowrank", "lowrank_s", "stack_lowrank_s")})
    out = []
    for c in cands:
        stem = c[len("stack_"):] if c.startswith("stack_") else c
        pre = "stack_" if c.startswith("stack_") else ""
        wins, rel = {}, []
        for (t, k) in sorted({(a, b) for a, b in zip(df.target, df["mask"])}):
            v = m[(t, k, c)]
            bars = {"knn": m[(t, k, "knn")], "lowrank": m[(t, k, "lowrank")], "stack_lowrank": m[(t, k, "stack_lowrank_s")]}
            for s in (0, 1):
                if (t, k, f"{pre}{stem}@null{s}") in m:
                    bars[f"null{s}"] = m[(t, k, f"{pre}{stem}@null{s}")]
            wins[(t, k)] = all(v <= 0.99 * b for b in bars.values())
            rel.append(v / bars["knn"])
        by_t = {t: all(wins.get((t, k), False) for k in ("MCAR", "MNAR")) for t in {a for a, _ in wins}}
        out.append({"method": c, "targets_won_both_masks": sum(by_t.values()), "qualifies": sum(by_t.values()) >= 2,
                    "mean_rel_to_knn": float(np.mean(rel)), "per_target": by_t})
    out.sort(key=lambda d: (not d["qualifies"], d["mean_rel_to_knn"]))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for t in TARGETS:
        precompute(t)
    jobs = [(t, n, k, s) for t, (_, regimes) in TARGETS.items() for n in regimes for k in ("MCAR", "MNAR") for s in SEEDS]
    with ProcessPoolExecutor(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4) as ex:
        rows = [r for rs in ex.map(run_config, jobs) for r in rs]
    (OUT / "dev_transfer.json").write_text(json.dumps({"seeds": SEEDS, "rows": rows}, indent=1) + "\n")
    sel = select(rows)
    (OUT / "dev_transfer_selection.json").write_text(json.dumps(sel, indent=1) + "\n")
    for d in sel:
        print(d)


if __name__ == "__main__":
    main()
