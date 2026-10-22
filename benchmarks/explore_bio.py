"""Amendment-13 DEV: biology-integrated model (BIM) vs stack3_plain / bim_null / kNN / kNN+low-rank, in-complex endpoint.

    python benchmarks/explore_bio.py     -> results/phase9/dev/dev_bio.json (+ selection)

Dev seeds 100-102 only. Holdouts (khan2023, derks2022, brunner2022) are never loaded or put in a reference.
"""

from __future__ import annotations

import itertools
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explore_reps import SEEDS, TARGETS  # noqa: E402
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp import refpanel as R  # noqa: E402
from scp_graphfs_mcp import transfer as T  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.priors import build_prior  # noqa: E402
from scp_graphfs_mcp.reps import pdb_costructure  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase9" / "dev"
CACHE = ROOT / "data" / "cache" / "transfer"
KAPPA = 0.25
G2 = (0.0, 0.25, 0.5, 0.75, 1.0)
GRID = {n: [w for w in itertools.product(G2, repeat=n) if abs(sum(w) - 1) < 1e-9] for n in (2, 3, 4)}


def phys_graph(names):
    U = nx.Graph()
    U.add_nodes_from(names)
    for G in (build_prior("complexportal", names), build_prior("corum", names), pdb_costructure.graph(names)):
        for u, v in G.edges():
            U.add_edge(u, v, weight=(U[u][v]["weight"] + 1) if U.has_edge(u, v) else 1.0)
    return U


def reference_datasets():
    ds = [d for d in T.extended_corpus() if d != T.AMENDMENT13_HOLDOUT]
    assert T.AMENDMENT13_HOLDOUT not in ds and not set(ds) & T.HOLDOUTS
    return ds


def precompute(tname: str, names, exclude, cache_name):
    f = CACHE / f"{cache_name}_bio.npz"
    if f.exists():
        return
    nb = R.neighbours_from_graph(phys_graph(names), names)
    nb_null = R.permute_neighbours(nb, 0)
    Z = np.vstack([T.corpus_reference(names, exclude, reference_datasets()), T.bulk_reference(names)])
    out = {}
    for key, kg, kap in (("plain", None, 0.0), ("kg", nb, KAPPA), ("kgnull", nb_null, KAPPA)):
        V, warm = T.fit_loadings(Z, kg=kg, kappa=kap)
        if kg is not None:
            V, usable = T.coldstart(V, warm, kg)
        else:
            usable = warm
        out[f"V_{key}"], out[f"u_{key}"] = V, usable
        print(f"[{time.strftime('%H:%M:%S')}] {cache_name} {key}: ref {Z.shape}, usable {usable.mean():.3f}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **out)


def evaluate(full, names, C, n_cells, kind, seed, strat_col="cell_type", per_type=None):
    """One subsample; returns {method: (squared errors all, in-complex mask)} plus chosen weights."""
    nb = R.neighbours_from_graph(phys_graph(names), names)
    nb_null = R.permute_neighbours(nb, 0)
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
    ct = full.obs[strat_col].values
    types = sorted(set(ct))
    if n_cells:
        rng = np.random.default_rng(seed)
        k = per_type or n_cells // len(types)
        idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], k, replace=False) for c in types]))
    else:
        idx = np.arange(full.n_obs)
    X = np.asarray(full.X, float)[idx]
    eligible = (~np.isnan(X)).mean(0) >= 0.5
    mask = make_mask(X, eligible, kind, seed)
    Xm = X.copy()
    Xm[mask] = np.nan
    truth = X[mask]
    sel = in_cx[np.nonzero(mask)[1]]
    rng = np.random.default_rng(seed + 7919)
    cand = np.argwhere(~np.isnan(Xm) & eligible[None, :])
    pick = cand[rng.choice(len(cand), max(1, int(0.1 * len(cand))), replace=False)]
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
    proj = {k: (T.project(Xm, C[f"V_{k}"], C[f"u_{k}"], base), T.project(Xi, C[f"V_{k}"], C[f"u_{k}"], bi))
            for k in ("plain", "kg", "kgnull")}
    rp = {"real": (R.rpr(Xm, nb, base=base), R.rpr(Xi, nb, base=bi)),
          "null": (R.rpr(Xm, nb_null, base=base), R.rpr(Xi, nb_null, base=bi))}
    preds, weights = {"knn": base, "lowrank": lr}, {}
    preds["stack_lowrank"], weights["stack_lowrank"] = stack([base, lr], [bi, lri])
    preds["stack3_plain"], weights["stack3_plain"] = stack([base, lr, proj["plain"][0]], [bi, lri, proj["plain"][1]])
    preds["stack3_kg"], weights["stack3_kg"] = stack([base, lr, proj["kg"][0]], [bi, lri, proj["kg"][1]])
    preds["bim"], weights["bim"] = stack([base, lr, proj["kg"][0], rp["real"][0]], [bi, lri, proj["kg"][1], rp["real"][1]])
    preds["bim_null"], weights["bim_null"] = stack([base, lr, proj["kgnull"][0], rp["null"][0]],
                                                   [bi, lri, proj["kgnull"][1], rp["null"][1]])
    se = {m: (Y[mask] - truth) ** 2 for m, Y in preds.items()}
    return se, sel, weights, len(idx)


def run_config(args):
    tname, n_cells, kind, seed = args
    full = TARGETS[tname][0]()
    names = list(full.var_names)
    C = dict(np.load(CACHE / f"{tname}_bio.npz"))
    se, sel, weights, n = evaluate(full, names, C, n_cells, kind, seed)
    rows = [{"target": tname, "n_cells": n, "mask": kind, "seed": seed, "method": m,
             "rmse_in_complex": float(np.sqrt(v[sel].mean())), "rmse_all": float(np.sqrt(v.mean())),
             "weights": weights.get(m)} for m, v in se.items()]
    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={n} {kind} {seed} done", flush=True)
    return rows


def select(rows):
    import pandas as pd

    df = pd.DataFrame(rows)
    df = df[df.n_cells <= 30]
    m = df.groupby(["target", "mask", "method"])["rmse_in_complex"].mean()
    res = {}
    for (t, k) in sorted({(a, b) for a, b in zip(df.target, df["mask"])}):
        v = m[(t, k, "bim")]
        a = all(v <= 0.99 * m[(t, k, b)] for b in ("knn", "stack_lowrank"))
        b = all(v <= 0.9975 * m[(t, k, c)] for c in ("stack3_plain", "bim_null"))
        res[(t, k)] = {"H13a": bool(a), "H13b": bool(b),
                       **{f"rel_{c}": float(v / m[(t, k, c)]) for c in ("knn", "stack_lowrank", "stack3_plain", "bim_null")}}
    by_t = {t: all(res[(t, k)]["H13a"] and res[(t, k)]["H13b"] for k in ("MCAR", "MNAR")) for t in {a for a, _ in res}}
    return {"per_target_mask": {f"{t}/{k}": v for (t, k), v in res.items()}, "targets_passing": by_t,
            "gate_passed": sum(by_t.values()) >= 2}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reference_datasets.json").write_text(json.dumps(reference_datasets(), indent=1) + "\n")
    for t in TARGETS:
        precompute(t, list(TARGETS[t][0]().var_names), (t,), t)
    jobs = [(t, n, k, s) for t, (_, regimes) in TARGETS.items() for n in regimes for k in ("MCAR", "MNAR") for s in SEEDS]
    with ProcessPoolExecutor(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4) as ex:
        rows = [r for rs in ex.map(run_config, jobs) for r in rs]
    (OUT / "dev_bio.json").write_text(json.dumps({"seeds": SEEDS, "kappa": KAPPA, "rows": rows}, indent=1) + "\n")
    sel = select(rows)
    (OUT / "dev_bio_selection.json").write_text(json.dumps(sel, indent=1) + "\n")
    print(json.dumps(sel, indent=1))


if __name__ == "__main__":
    main()
