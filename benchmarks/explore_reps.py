"""Amendment-9 DEV: exhaustive representation sweep (RPR, RPR-stack, pkNN) with nulls and data-only controls.

    python benchmarks/explore_reps.py                 -> results/phase6/dev/dev_reps.json (+ coverage, selection)
    python benchmarks/explore_reps.py --normalise median --only <rep> <estimator>   (robustness check, selected pair)

Dev seeds 100-102 only. The holdout (khan2023) is never loaded here.
"""

from __future__ import annotations

import importlib
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import features as FT  # noqa: E402
from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp import refpanel as R  # noqa: E402
from scp_graphfs_mcp.datasets import load_leduc2022, load_petrosius2023, load_specht2021  # noqa: E402
from scp_graphfs_mcp.imc import permuted_features  # noqa: E402
from scp_graphfs_mcp.priors import build_prior  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase6" / "dev"
SEEDS = [100, 101, 102]
TARGETS = {"petrosius2023": (load_petrosius2023, [30, 0]), "leduc2022": (load_leduc2022, [30, 200]),
           "specht2021": (load_specht2021, [30, 200])}
CURATED_PRIORS = ["complexportal", "corum", "string", "humap3"]
# (module, kind) for Amendment-9 sources; a module that is absent or raises is dropped and reported.
NEW_GRAPHS = ["pdb_costructure", "reactome", "biogrid", "intact", "cocitation", "indra", "pathwaycommons"]
NEW_FEATURES = [("prott5", "block"), ("pharos", "block"), ("monarch", "block"), ("monarch", "disease_block")]
NEW_REFERENCES = ["ccle", "proteomehd"]
MIN_COVERAGE = 0.20


def _mod(name):
    return importlib.import_module(f"scp_graphfs_mcp.reps.{name}")


def _graph_cov(G, names):
    return float(np.mean([G.degree(v) > 0 if v in G else False for v in names]))


def build_reps(tname: str, names: list[str]):
    """name -> {"rpr": neighbour lists, "signed": bool, "F": feature block for pkNN, "cov": coverage}."""
    reps, report = {}, {}
    graphs = {}

    def add_graph(key, G, F=None):
        cov = _graph_cov(G, names)
        report[key] = {"kind": "graph", "coverage": cov, "edges": G.number_of_edges()}
        if cov < MIN_COVERAGE:
            report[key]["dropped"] = "coverage < 20%"
            return
        graphs[key] = G
        reps[key] = {"rpr": R.neighbours_from_graph(G, names), "signed": False,
                     "F": F if F is not None else FT.spectral_block(G, names)}

    def add_features(key, F):
        cov = float(F[:, -1].mean())
        report[key] = {"kind": "features", "coverage": cov, "dim": int(F.shape[1] - 1)}
        if cov < MIN_COVERAGE:
            report[key]["dropped"] = "coverage < 20%"
            return
        reps[key] = {"rpr": R.neighbours_from_features(F), "signed": False, "F": F}

    for p in CURATED_PRIORS:
        add_graph(p, build_prior(p, names))
    for g in NEW_GRAPHS:
        try:
            m = _mod(g)
        except ModuleNotFoundError:
            continue
        try:
            add_graph(g, m.graph(names), m.block(names) if hasattr(m, "block") else None)
        except Exception as e:  # noqa: BLE001
            report[g] = {"kind": "graph", "dropped": f"error: {type(e).__name__}: {e}"}
    feats = {"go": FT.go_block(names), "hpa": FT.hpa_block(names), "uniprot_kw": FT.uniprot_keywords_block(names),
             "physical": FT.physical_block(names), "corpus": FT.corpus_loadings_block(names, (tname,))}
    for mod, fn in NEW_FEATURES:
        key = mod if fn == "block" else f"{mod}_{fn.replace('_block', '')}"
        try:
            feats[key] = getattr(_mod(mod), fn)(names)
        except ModuleNotFoundError:
            continue
        except Exception as e:  # noqa: BLE001
            report[key] = {"kind": "features", "dropped": f"error: {type(e).__name__}: {e}"}
    for k, F in feats.items():
        add_features(k, F)
    for r in NEW_REFERENCES:
        try:
            m = _mod(r)
        except ModuleNotFoundError:
            continue
        try:
            Rf, has = m.reference(names)
            cov = float(np.mean(has))
            report[r] = {"kind": "reference", "coverage": cov, "lines": int(Rf.shape[1])}
            if cov < MIN_COVERAGE:
                report[r]["dropped"] = "coverage < 20%"
                continue
            reps[r] = {"rpr": R.neighbours_from_reference(Rf, np.asarray(has, bool)), "signed": True,
                       "F": m.block(names)}
        except Exception as e:  # noqa: BLE001
            report[r] = {"kind": "reference", "dropped": f"error: {type(e).__name__}: {e}"}
    # combined representations
    U = nx.Graph()
    U.add_nodes_from(names)
    for G in graphs.values():
        for u, v in G.edges():
            w = U[u][v]["weight"] + 1 if U.has_edge(u, v) else 1.0
            U.add_edge(u, v, weight=w)
    add_graph("union_curated", U)
    add_features("concat_features", np.hstack([F for k, F in feats.items() if k in reps]))
    return reps, report


def _rmse(Y, mask, truth):
    return float(np.sqrt(np.mean((Y[mask] - truth) ** 2)))


def run_config(args):
    tname, n_cells, kind, seed, normalise, only = args
    loader, _ = TARGETS[tname]
    full = loader()
    names = list(full.var_names)
    reps, _ = build_reps(tname, names)
    if only:
        reps = {k: v for k, v in reps.items() if k == only[0]}
    ct = full.obs["cell_type"].values
    types = sorted(set(ct))
    if n_cells:
        rng = np.random.default_rng(seed)
        idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], n_cells // len(types), replace=False)
                                      for c in types]))
    else:
        idx = np.arange(full.n_obs)
    X = np.asarray(full.X, float)[idx]
    if normalise == "median":
        X = X - np.nanmedian(X, axis=1, keepdims=True)
    eligible = (~np.isnan(X)).mean(0) >= 0.5
    mask = make_mask(X, eligible, kind, seed)
    Xm = X.copy()
    Xm[mask] = np.nan
    truth = X[mask]
    rows = []

    def rec(method, rep, Y, w=None):
        rows.append({"target": tname, "n_cells": int(len(idx)), "mask": kind, "seed": seed, "normalise": normalise,
                     "method": method, "rep": rep, "rmse_all": _rmse(Y, mask, truth), "stack_w": w})

    # shared inner split for every stack (same rule as refpanel.stack_with_base, computed once)
    rng = np.random.default_rng(seed + 7919)
    cand = np.argwhere(~np.isnan(Xm) & eligible[None, :])
    pick = cand[rng.choice(len(cand), max(1, int(0.1 * len(cand))), replace=False)]
    Xi = Xm.copy()
    Xi[pick[:, 0], pick[:, 1]] = np.nan
    ti = Xm[pick[:, 0], pick[:, 1]]
    base = P._fill(Xm, P.loo_knn(Xm))
    bi = P._fill(Xi, P.loo_knn(Xi))
    grid = (0.0, 0.25, 0.5, 0.75, 1.0)

    def stack(make_other):
        oi = make_other(Xi, bi)
        a, b = bi[pick[:, 0], pick[:, 1]], oi[pick[:, 0], pick[:, 1]]
        w = grid[int(np.argmin([np.mean((w * a + (1 - w) * b - ti) ** 2) for w in grid]))]
        return w * base + (1 - w) * make_other(Xm, base), w

    if not only:
        rec("knn", "-", base)
        lr = P.grmf(Xm, None, names, lam_g=0.0)
        rec("lowrank", "-", lr)
        Y, w = stack(lambda A, b: P.grmf(A, None, names, lam_g=0.0))
        rec("stack_lowrank", "-", Y, w)
        rec("rpr", "data", R.rpr(Xm, R.neighbours_from_data(Xm), base=base))
        Y, w = stack(lambda A, b: R.rpr(A, R.neighbours_from_data(A), base=b))
        rec("rpr_stack", "data", Y, w)
        if n_cells and n_cells <= 30:
            rec("pknn", "data", P.protein_specific_knn(Xm, P.neighbour_sets_from_data(Xm)))
    for key, r in reps.items():
        variants = {"": r["rpr"], "@null0": R.permute_neighbours(r["rpr"], 0), "@null1": R.permute_neighbours(r["rpr"], 1)}
        for sfx, nb in variants.items():
            rec("rpr", key + sfx, R.rpr(Xm, nb, base=base, signed=r["signed"]))
            Y, w = stack(lambda A, b, nb=nb: R.rpr(A, nb, base=b, signed=r["signed"]))
            rec("rpr_stack", key + sfx, Y, w)
        if n_cells and n_cells <= 30:
            rec("pknn", key, P.protein_specific_knn(Xm, P.neighbour_sets_from_features(r["F"])))
            for s in (0, 1):
                rec("pknn", f"{key}@null{s}", P.protein_specific_knn(Xm, P.neighbour_sets_from_features(permuted_features(r["F"], s))))
    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} done ({len(rows)} rows)", flush=True)
    return rows


def select(rows):
    """Amendment-9 selection rule on the 30-cell regime."""
    import pandas as pd

    df = pd.DataFrame(rows)
    df = df[df.n_cells <= 30]
    m = df.groupby(["target", "mask", "method", "rep"])["rmse_all"].mean()
    out = []
    for (est, rep) in sorted({(a, b) for a, b in zip(df.method, df.rep) if b not in ("-", "data") and "@" not in b}):
        wins, rel = {}, []
        for (t, k) in sorted({(a, b) for a, b in zip(df.target, df["mask"])}):
            v = m.get((t, k, est, rep))
            if v is None:
                continue
            bars = {"knn": m[(t, k, "knn", "-")], "lowrank": m[(t, k, "lowrank", "-")],
                    "stack_lowrank": m[(t, k, "stack_lowrank", "-")], "rpr_data": m[(t, k, "rpr", "data")],
                    "rpr_stack_data": m[(t, k, "rpr_stack", "data")]}
            if (t, k, "pknn", "data") in m:
                bars["pknn_data"] = m[(t, k, "pknn", "data")]
            for s in (0, 1):
                if (t, k, est, f"{rep}@null{s}") in m:
                    bars[f"null{s}"] = m[(t, k, est, f"{rep}@null{s}")]
            wins[(t, k)] = all(v <= 0.99 * b for b in bars.values())
            rel.append(v / bars["knn"])
        by_t = {t: all(wins.get((t, k), False) for k in ("MCAR", "MNAR")) for t in {a for a, _ in wins}}
        out.append({"estimator": est, "rep": rep, "targets_won_both_masks": sum(by_t.values()),
                    "qualifies": sum(by_t.values()) >= 2, "mean_rel_to_knn": float(np.mean(rel)) if rel else None,
                    "per_target": by_t})
    out.sort(key=lambda d: (not d["qualifies"], d["mean_rel_to_knn"] if d["mean_rel_to_knn"] is not None else 9))
    return out


def main():
    normalise = "none"
    only = None
    if "--normalise" in sys.argv:
        normalise = sys.argv[sys.argv.index("--normalise") + 1]
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        only = (sys.argv[i + 1], sys.argv[i + 2])
    OUT.mkdir(parents=True, exist_ok=True)
    reports = {}
    for t, (loader, _) in TARGETS.items():
        reports[t] = build_reps(t, list(loader().var_names))[1]
    (OUT / "reps_coverage.json").write_text(json.dumps(reports, indent=1) + "\n")
    jobs = [(t, n, k, s, normalise, only) for t, (_, regimes) in TARGETS.items() for n in regimes
            for k in ("MCAR", "MNAR") for s in SEEDS]
    with ProcessPoolExecutor(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4) as ex:
        rows = [r for rs in ex.map(run_config, jobs) for r in rs]
    tag = "dev_reps" if not only else f"dev_reps_robust_{normalise}_{only[0]}"
    (OUT / f"{tag}.json").write_text(json.dumps({"seeds": SEEDS, "normalise": normalise, "rows": rows}, indent=1) + "\n")
    if not only:
        sel = select(rows)
        (OUT / "dev_reps_selection.json").write_text(json.dumps(sel, indent=1) + "\n")
        for d in sel[:15]:
            print(d)


if __name__ == "__main__":
    main()
