"""Benchmark: curated complex priors vs kNN / STRING / shuffled nulls.

Implements benchmarks/PREREGISTRATION.md exactly. Usage::

    python benchmarks/run.py                     # core -> results/
    python benchmarks/run.py --include-contrib   # core + contrib rows -> results/contrib/ only
    python benchmarks/run.py --quick             # 2 seeds, 3 nulls, 200 bootstraps -> benchmarks/_quick_out/

Fixed seeds throughout; identical inputs give identical outputs.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import f1_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

from scp_graphfs_mcp.complexes import in_any_complex, load_complexes
from scp_graphfs_mcp.datasets import from_log2_matrix, load_petrosius2023
from scp_graphfs_mcp.ids import group_accessions, symbols_for_accession
from scp_graphfs_mcp.methods import (adjacency, impute_mean, impute_with_prior, knn_fill, partner_zscores,
                                     select_features, select_random)
from scp_graphfs_mcp.priors import build_prior, nulls as make_nulls
from scp_graphfs_mcp.registry import METHODS, PRIORS, load_contrib

ROOT = Path(__file__).resolve().parents[1]
CORE_PRIORS = ["corum", "complexportal", "string_exp", "string"]
CURATED = ["corum", "complexportal"]
KS = [25, 50, 100]
# A CI upper bound must be below -SIG_TOL to count as an improvement: identical predictions
# (e.g. kNN fallback on both sides) otherwise produce float noise around -1e-14.
SIG_TOL = 1e-9


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- setup


def median_normalise(adata):
    """Exploratory only (not preregistered): subtract each cell's median observed log2 value,
    add back the global median. Keeps NaN; rebuilds layers['raw']."""
    X = np.asarray(adata.X, float)
    Xn = X - np.nanmedian(X, axis=1, keepdims=True) + np.nanmedian(X)
    out = from_log2_matrix(Xn, adata.obs_names, adata.var_names, obs=adata.obs)
    out.uns = dict(adata.uns)
    return out


def setup(n_nulls: int, include_contrib: bool, normalise: str = "none"):
    adata = load_petrosius2023()
    if normalise == "median":
        adata = median_normalise(adata)
    ids = list(adata.var_names)
    prior_names = list(CORE_PRIORS)
    if include_contrib:
        load_contrib()
        prior_names += [n for n, e in PRIORS.items() if e.contrib]
    priors, null_graphs = {}, {}
    for name in prior_names:
        g = build_prior(name, ids)
        priors[name] = g
        null_graphs[name] = make_nulls(g, n_nulls)  # auto-null for every prior, contrib included
        log(f"prior {name}: {g.number_of_edges()} edges, {g.graph['coverage']['n_with_edges']} proteins with edges")
    in_cx = np.array([in_any_complex(group_accessions(f)) for f in ids])
    return adata, priors, null_graphs, in_cx


def strata(in_cx_cols: np.ndarray) -> dict[str, np.ndarray]:
    return {"all": np.ones_like(in_cx_cols, bool), "in_complex": in_cx_cols, "not_in_complex": ~in_cx_cols}


# --------------------------------------------------------------------------- test 1: imputation


def make_mask(X: np.ndarray, eligible: np.ndarray, kind: str, seed: int, frac: float = 0.1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    obs = ~np.isnan(X) & eligible[None, :]
    r, c = np.nonzero(obs)
    n = int(round(frac * len(r)))
    if kind == "MCAR":
        w = np.ones(len(r))
    elif kind == "MNAR":
        q25 = np.nanpercentile(X, 25, axis=0)
        sd = np.nanstd(X, axis=0)
        w = expit((q25[c] - X[r, c]) / (0.5 * np.where(sd > 0, sd, 1.0)[c]))
    else:
        raise ValueError(kind)
    pick = rng.choice(len(r), size=n, replace=False, p=w / w.sum())
    m = np.zeros_like(obs)
    m[r[pick], c[pick]] = True
    return m


def boot_rmse_diff(se_a: np.ndarray, se_b_list: list[np.ndarray], n_boot: int, seed: int):
    """Paired bootstrap over masked entries of RMSE(a) - mean_i RMSE(b_i)."""
    rng = np.random.default_rng(seed)
    n = len(se_a)
    B = np.vstack(se_b_list).astype(np.float64)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        diffs[i] = np.sqrt(se_a[idx].mean()) - np.sqrt(B[:, idx].mean(axis=1)).mean()
    point = np.sqrt(se_a.mean()) - np.sqrt(B.mean(axis=1)).mean()
    d = se_a - B.mean(axis=0)
    dz = float(d.mean() / d.std()) if d.std() > 0 else 0.0
    return {"delta_rmse": float(point), "ci95": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))],
            "effect_size_dz_sqerr": dz, "n_entries": int(n)}


def test_imputation(adata, priors, null_graphs, in_cx, seeds, n_boot):
    X = np.asarray(adata.X, float)
    det = (~np.isnan(X)).mean(0)
    eligible = det >= 0.5
    out = {"eligible_proteins": int(eligible.sum()), "masks": {}}
    for kind in ["MCAR", "MNAR"]:
        se: dict[str, list] = {}
        r_by_seed: dict[str, dict] = {}
        col_of_entry, fallback_entry = [], {}
        for seed in seeds:
            mask = make_mask(X, eligible, kind, seed)
            Xm = X.copy()
            Xm[mask] = np.nan
            am = from_log2_matrix(Xm, adata.obs_names, adata.var_names)
            truth = X[mask]
            knn = knn_fill(am)
            preds = {"mean": impute_mean(am), "knn": knn}
            for name, g in priors.items():
                res = impute_with_prior(am, g, fallback=knn)
                preds[name] = np.asarray(res.X)
                fallback_entry.setdefault(name, []).append(~res.layers["imputed_by_prior"][mask])
                for i, h in enumerate(null_graphs[name]):
                    preds[f"{name}__null{i}"] = np.asarray(impute_with_prior(am, h, fallback=knn).X)
            _, cols = np.nonzero(mask)
            col_of_entry.append(cols)
            for m, P in preds.items():
                e = P[mask] - truth
                se.setdefault(m, []).append(e ** 2)
                r_by_seed.setdefault(m, {})[seed] = {
                    s: float(np.corrcoef(P[mask][sel], truth[sel])[0, 1])
                    for s, sel in strata(in_cx[cols]).items()}
            log(f"imputation {kind} seed {seed}: {mask.sum()} masked entries")
        cols = np.concatenate(col_of_entry)
        SE = {m: np.concatenate(v) for m, v in se.items()}
        S = strata(in_cx[cols])
        rows = []
        for m in SE:
            for s, sel in S.items():
                rows.append({"method": m, "stratum": s, "rmse": float(np.sqrt(SE[m][sel].mean())),
                             "pearson_r_by_seed": [r_by_seed[m][sd][s] for sd in seeds],
                             "n_entries": int(sel.sum())})
        comps = []
        for name in priors:
            nulls_ = [f"{name}__null{i}" for i in range(len(null_graphs[name]))]
            fb = np.concatenate(fallback_entry[name])
            for s, sel in S.items():
                for ref, refs in [("knn", ["knn"]), ("own_null_mean", nulls_)]:
                    c = boot_rmse_diff(SE[name][sel], [SE[r][sel] for r in refs], n_boot, seed=17)
                    null_rmses = [float(np.sqrt(SE[r][sel].mean())) for r in nulls_]
                    comps.append({"prior": name, "vs": ref, "stratum": s, **c,
                                  "rmse_prior": float(np.sqrt(SE[name][sel].mean())),
                                  "rmse_ref": float(np.mean([np.sqrt(SE[r][sel].mean()) for r in refs])),
                                  "null_rmse_range": [min(null_rmses), max(null_rmses)] if ref != "knn" else None,
                                  "frac_entries_imputed_by_prior": float(1 - fb[sel].mean()),
                                  "significant_improvement": c["ci95"][1] < -SIG_TOL})
        out["masks"][kind] = {"rows": rows, "comparisons": comps}
    return out


# --------------------------------------------------------------------------- test 2/sanity/stretch: panels


def panel_r2(Xknn: np.ndarray, Xobs: np.ndarray, panel_idx, target_mask, in_cx, seed=0):
    tgt = np.where(target_mask)[0]
    tgt = tgt[~np.isin(tgt, panel_idx)]
    F, T = Xknn[:, panel_idx], Xknn[:, tgt]
    pred = np.zeros_like(T)
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(F):
        sc = StandardScaler().fit(F[tr])
        mu = T[tr].mean(0)
        model = Ridge(alpha=1.0).fit(sc.transform(F[tr]), T[tr] - mu)
        pred[te] = model.predict(sc.transform(F[te])) + mu
    Y = Xobs[:, tgt]
    obs = ~np.isnan(Y)
    r2 = np.full(len(tgt), np.nan)
    for j in range(len(tgt)):
        y, p = Y[obs[:, j], j], pred[obs[:, j], j]
        if len(y) >= 10 and y.var() > 0:
            r2[j] = 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    st = strata(in_cx[tgt])
    return {s: float(np.nanmean(r2[sel])) for s, sel in st.items()}


def panels_for(adata, priors, null_graphs, k, random_seeds, extra_methods=()):
    names = list(adata.var_names)
    P = {"hvp": select_features(adata, None, k, "none")}
    for s in random_seeds:
        P[f"random__{s}"] = select_random(adata, k, s)
    for name, g in priors.items():
        P[name] = select_features(adata, g, k, "soft_weight")
        for i, h in enumerate(null_graphs[name]):
            P[f"{name}__null{i}"] = select_features(adata, h, k, "soft_weight")
    for m in extra_methods:
        for name, g in priors.items():
            P[f"{m}:{name}"] = list(METHODS[m].select(adata, g, k))
    return {m: [names.index(p) for p in v] for m, v in P.items()}


def summarise(per_method: dict, priors, n_nulls, random_seeds, key=None):
    get = (lambda v: v[key]) if key else (lambda v: v)
    out = {"hvp": get(per_method["hvp"]),
           "random_mean": float(np.mean([get(per_method[f"random__{s}"]) for s in random_seeds]))}
    for name in priors:
        nv = [get(per_method[f"{name}__null{i}"]) for i in range(n_nulls)]
        out[name] = get(per_method[name])
        out[f"{name}__null_mean"] = float(np.mean(nv))
        out[f"{name}__null_range"] = [float(min(nv)), float(max(nv))]
    for m in per_method:
        if ":" in m:
            out[m] = get(per_method[m])
    return out


def test_panel(adata, priors, null_graphs, in_cx, n_nulls, random_seeds, extra_methods):
    X = np.asarray(adata.X, float)
    Xknn = knn_fill(adata)
    target = (~np.isnan(X)).mean(0) >= 0.5
    res = {}
    for k in KS:
        P = panels_for(adata, priors, null_graphs, k, random_seeds, extra_methods)
        per = {m: panel_r2(Xknn, X, idx, target, in_cx) for m, idx in P.items()}
        res[str(k)] = {s: summarise(per, priors, n_nulls, random_seeds, s) for s in ["all", "in_complex", "not_in_complex"]}
        res[str(k)]["panels"] = {m: [adata.var_names[i] for i in idx] for m, idx in P.items()
                                 if "__null" not in m and "random__" not in m}
        log(f"panel k={k} done")
    return res, Xknn


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b)


def test_stability(adata, priors, null_graphs, n_boot_cells, k=50):
    names = list(adata.var_names)
    sel: dict[str, list] = {}
    for b in range(n_boot_cells):
        idx = np.random.default_rng(b).integers(0, adata.n_obs, adata.n_obs)
        sub = adata[idx].copy()
        sub.obs_names_make_unique()
        sel.setdefault("hvp", []).append(select_features(sub, None, k, "none"))
        sel.setdefault("random", []).append(select_random(sub, k, b))
        for name, g in priors.items():
            sel.setdefault(name, []).append(select_features(sub, g, k, "soft_weight"))
            for i, h in enumerate(null_graphs[name]):
                sel.setdefault(f"{name}__null{i}", []).append(select_features(sub, h, k, "soft_weight"))
    mj = {m: float(np.mean([jaccard(v[i], v[j]) for i in range(len(v)) for j in range(i + 1, len(v))]))
          for m, v in sel.items()}
    out = {"k": k, "n_bootstraps": n_boot_cells, "hvp": mj["hvp"], "random": mj["random"]}
    for name in priors:
        nv = [mj[f"{name}__null{i}"] for i in range(len(null_graphs[name]))]
        out[name] = mj[name]
        out[f"{name}__null_mean"] = float(np.mean(nv))
        out[f"{name}__null_range"] = [float(min(nv)), float(max(nv))]
    log("stability done")
    return out


def test_classification(adata, Xknn, priors, null_graphs, random_seeds, k=50):
    y = adata.obs["cell_type"].values
    names = list(adata.var_names)

    def f1(idx):
        pred = np.empty_like(y)
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(Xknn, y):
            sc = StandardScaler().fit(Xknn[tr][:, idx])
            clf = LogisticRegression(max_iter=5000).fit(sc.transform(Xknn[tr][:, idx]), y[tr])
            pred[te] = clf.predict(sc.transform(Xknn[te][:, idx]))
        return float(f1_score(y, pred, average="macro"))

    P = panels_for(adata, priors, null_graphs, k, random_seeds)
    per = {m: f1(idx) for m, idx in P.items()}
    out = summarise(per, priors, len(next(iter(null_graphs.values()))), random_seeds)
    out["all_proteins_detected_ge_50pct"] = f1(np.where((~np.isnan(np.asarray(adata.X))).mean(0) >= .5)[0])
    out["k"] = k
    out["ceiling_flag"] = out["random_mean"] >= 0.9
    out["note"] = "Sanity check only; not evidence for the claim."
    log("classification done")
    return out


def test_cross_context(adata, priors, null_graphs, in_cx, random_seeds, k=50):
    ct = adata.obs["cell_type"].values
    src = adata[np.isin(ct, ["LSC", "prog"])].copy()
    dst = adata[np.isin(ct, ["CD38_pos", "CD38_neg"])].copy()
    Xd = np.asarray(dst.X, float)
    Xd_knn = knn_fill(dst)
    target = (~np.isnan(Xd)).mean(0) >= 0.5
    P = panels_for(src, priors, null_graphs, k, random_seeds)
    per = {m: panel_r2(Xd_knn, Xd, idx, target, in_cx) for m, idx in P.items()}
    out = {s: summarise(per, priors, len(next(iter(null_graphs.values()))), random_seeds, s)
           for s in ["all", "in_complex", "not_in_complex"]}
    out.update({"k": k, "select_on": ["LSC", "prog"], "evaluate_on": ["CD38_pos", "CD38_neg"],
                "n_cells_select": int(src.n_obs), "n_cells_eval": int(dst.n_obs)})
    log("cross-context done")
    return out


# --------------------------------------------------------------------------- discordance


def union_graph(a: nx.Graph, b: nx.Graph) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(a.nodes)
    for src in (a, b):
        for u, v, w in src.edges(data="weight"):
            g.add_edge(u, v, weight=(g.edges[u, v]["weight"] if g.has_edge(u, v) else 0.0) + w)
    g.graph["provenance"] = {"source": "CORUM+ComplexPortal", "version": "-", "url": "-", "sha256": "-"}
    return g


def partner_corr(X, g, names, cols):
    zhat, support, mu, sd = partner_zscores(X, adjacency(g, names))
    Z = (X - mu) / sd
    r = np.full(len(cols), np.nan)
    npart = np.zeros(len(cols), int)
    for t, j in enumerate(cols):
        ok = ~np.isnan(Z[:, j]) & (support[:, j] > 0)
        npart[t] = int(np.median(support[ok, j] > 0)) if ok.any() else 0
        if ok.sum() >= 30 and Z[ok, j].std() > 0 and zhat[ok, j].std() > 0:
            r[t] = np.corrcoef(Z[ok, j], zhat[ok, j])[0, 1]
    return r


def discordance(adata, priors, n_nulls, in_cx):
    X = np.asarray(adata.X, float)
    names = list(adata.var_names)
    U = union_graph(priors["corum"], priors["complexportal"])
    det = (~np.isnan(X)).mean(0)
    cols = np.where((det >= 0.8) & in_cx & np.array([U.degree(n) > 0 for n in names]))[0]
    r = partner_corr(X, U, names, cols)
    from scp_graphfs_mcp.priors import shuffled_null
    R0 = np.vstack([partner_corr(X, shuffled_null(U, s), names, cols) for s in range(n_nulls)])
    null_mean, null_sd = np.nanmean(R0, 0), np.nanstd(R0, 0)
    cx = load_complexes()
    rows = []
    for t, j in enumerate(cols):
        f = names[j]
        accs = group_accessions(f)
        cnames = sorted({n for a in accs for n, m in zip(cx["name"], cx["members"]) if a in m})
        rows.append({"protein": f, "symbols": ";".join(sorted({s for a in accs for s in symbols_for_accession(a)})),
                     "n_complexes": len(cnames), "example_complexes": " | ".join(cnames[:3]),
                     "n_partners_in_dataset": int(U.degree(f)), "detection": round(float(det[j]), 3),
                     "r_with_partners": r[t], "null_mean_r": null_mean[t], "null_sd_r": null_sd[t],
                     "discordance_z": (null_mean[t] - r[t]) / null_sd[t] if null_sd[t] > 0 else np.nan,
                     "label": "hypothesis (possible database error or moonlighting outside the complex), not a finding"})
    df = pd.DataFrame(rows).sort_values("discordance_z", ascending=False, na_position="last")
    log(f"discordance: {len(df)} proteins scored")
    return df


# --------------------------------------------------------------------------- verdicts


def verdicts(imp, panel, stab):
    v = {}
    ok_all = []
    for name in CURATED:
        per_mask = {}
        for kind, d in imp["masks"].items():
            c = {(x["vs"]): x for x in d["comparisons"] if x["prior"] == name and x["stratum"] == "in_complex"}
            per_mask[kind] = bool(c["knn"]["significant_improvement"] and c["own_null_mean"]["significant_improvement"])
        v[f"test1_{name}"] = per_mask
        ok_all.append(all(per_mask.values()))
    v["test1_pass"] = any(ok_all)
    t2 = {}
    for name in CURATED:
        wins = sum(panel[str(k)]["all"][name] > max(panel[str(k)]["all"]["hvp"], panel[str(k)]["all"][f"{name}__null_mean"])
                   for k in KS)
        t2[name] = int(wins)
    v["test2_wins_out_of_3"] = t2
    v["test2_pass"] = any(w >= 2 for w in t2.values())
    v["test3"] = {name: bool(stab[name] > stab["hvp"] and stab[name] > stab[f"{name}__null_mean"]) for name in CURATED}
    v["test3_pass"] = any(v["test3"].values())
    rm = {}
    for kind, d in imp["masks"].items():
        rm[kind] = {r["method"]: r["rmse"] for r in d["rows"] if r["stratum"] == "in_complex"
                    and r["method"] in ("corum", "complexportal", "string_exp", "string")}
    v["test4_in_complex_rmse"] = rm
    v["test4_pass"] = all(min(m["corum"], m["complexportal"]) <= m["string_exp"] <= m["string"] for m in rm.values())
    return v


# --------------------------------------------------------------------------- main


def _jsonable(o):
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    raise TypeError(type(o))


def write(out_dir: Path, name: str, obj) -> None:
    (out_dir / name).write_text(json.dumps(obj, indent=1, default=_jsonable, allow_nan=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-contrib", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--normalise", choices=["none", "median"], default="none",
                    help="EXPLORATORY (not preregistered): per-cell median normalisation; writes to results/exploratory/")
    a = ap.parse_args(argv)
    if a.quick:
        seeds, n_nulls, n_boot, random_seeds, n_stab = [0, 1], 3, 200, list(range(3)), 5
    else:
        seeds, n_nulls, n_boot, random_seeds, n_stab = [0, 1, 2, 3, 4], 10, 1000, list(range(10)), 20
    if a.normalise != "none" and a.out is None:
        a.out = ROOT / "results" / "exploratory" / f"normalise_{a.normalise}"
    out_dir = a.out or (ROOT / "results" / "contrib" if a.include_contrib
                        else ROOT / "benchmarks" / "_quick_out" if a.quick else ROOT / "results")
    core = (ROOT / "results").resolve()
    od = out_dir.resolve()
    under = od == core or core in od.parents
    if a.include_contrib and under and not (od == core / "contrib" or (core / "contrib") in od.parents):
        sys.exit("refusing: --include-contrib may only write under results/contrib/")
    if a.normalise != "none" and under and not (core / "exploratory") in od.parents:
        sys.exit("refusing: exploratory runs may only write under results/exploratory/")
    if a.quick and under:
        sys.exit("refusing: --quick may not write under results/")
    if under and od != core and not a.include_contrib and a.normalise == "none":
        sys.exit("refusing: a core run writes to results/ itself, not a subdirectory")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:  # recorded at start: the code that actually runs
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        commit = None
    t0 = time.time()
    adata, priors, null_graphs, in_cx = setup(n_nulls, a.include_contrib, a.normalise)
    extra = [m for m, e in METHODS.items() if e.contrib and e.select is not None] if a.include_contrib else []

    imp = test_imputation(adata, priors, null_graphs, in_cx, seeds, n_boot)
    write(out_dir, "imputation.json", imp)
    panel, Xknn = test_panel(adata, priors, null_graphs, in_cx, n_nulls, random_seeds, extra)
    write(out_dir, "panel.json", panel)
    stab = test_stability(adata, priors, null_graphs, n_stab)
    write(out_dir, "stability.json", stab)
    write(out_dir, "classification.json", test_classification(adata, Xknn, priors, null_graphs, random_seeds))
    write(out_dir, "cross_context.json", test_cross_context(adata, priors, null_graphs, in_cx, random_seeds))
    discordance(adata, priors, n_nulls, in_cx).to_csv(out_dir / "discordant_subunits.csv", index=False,
                                                      float_format="%.4f")
    v = verdicts(imp, panel, stab)
    write(out_dir, "verdicts.json", v)
    coverage = {n: {k: x for k, x in g.graph["coverage"].items() if k != "unmapped"} for n, g in priors.items()}
    coverage["_dataset"] = {"n_cells": adata.n_obs, "n_proteins": adata.n_vars,
                            "missing_fraction": float(np.isnan(np.asarray(adata.X)).mean()),
                            "n_in_complex": int(in_cx.sum()),
                            "cell_types": adata.obs["cell_type"].value_counts().to_dict()}
    coverage["_nulls"] = {n: [h.graph["provenance"]["n_swaps"] for h in hs] for n, hs in null_graphs.items()}
    write(out_dir, "coverage.json", coverage)
    write(out_dir, "run_meta.json", {
        "code_commit": commit, "quick": a.quick, "include_contrib": a.include_contrib,
        "normalise": a.normalise, "preregistered": a.normalise == "none" and not a.quick,
        "seeds": seeds, "n_nulls": n_nulls, "n_bootstrap": n_boot, "random_seeds": random_seeds,
        "n_stability_bootstraps": n_stab, "runtime_seconds": round(time.time() - t0, 1),
        "python": platform.python_version(),
        "versions": {p: version(p) for p in ["numpy", "scipy", "scikit-learn", "anndata", "networkx", "scp-prep"]},
    })
    log(f"done in {time.time() - t0:.0f}s -> {out_dir}")
    print(json.dumps(v, indent=1, default=_jsonable))


if __name__ == "__main__":
    main()
