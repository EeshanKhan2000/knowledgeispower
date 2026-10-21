"""External evidence for priors (EXPLORATION.md Amendment 4): co-variation pooled across OTHER datasets.

The corpus lives in data/cache/corpus/*.npz (built by scripts/build_corpus.py). For a target dataset, the
target itself must be excluded (leave-one-dataset-out), and the holdouts (khan2023, derks2022) are never in
the corpus.
"""

from __future__ import annotations

from functools import lru_cache

import networkx as nx
import numpy as np

from .ids import DATA_DIR, group_accessions

CORPUS_DIR = DATA_DIR / "cache" / "corpus"
CORPUS = ["petrosius2023", "leduc2022", "specht2021", "schoof2021", "woo2022"]
HOLDOUTS = {"khan2023", "derks2022"}


@lru_cache(maxsize=8)
def _load(name):
    d = np.load(CORPUS_DIR / f"{name}.npz")
    return d["X"].astype(float), [str(a) for a in d["accs"]]


def pooled_corr(var_names, exclude: tuple[str, ...], min_overlap: int = 20):
    """Fisher-z average (weighted by co-observed cell count) of protein-protein Pearson r across corpus
    datasets other than `exclude`, over the target's features (first accession of each group).
    Returns (R, n_datasets) as p x p arrays (R = nan where no dataset informs the pair)."""
    if set(exclude) & HOLDOUTS:
        raise ValueError("holdouts are never part of the corpus")
    target = [(group_accessions(f) or [""])[0] for f in var_names]
    p = len(target)
    zsum = np.zeros((p, p))
    wsum = np.zeros((p, p))
    nds = np.zeros((p, p), int)
    for name in CORPUS:
        if name in exclude:
            continue
        X, accs = _load(name)
        pos = {a: i for i, a in enumerate(accs)}
        idx_t = np.array([i for i, a in enumerate(target) if a in pos])
        if len(idx_t) < 2:
            continue
        Xs = X[:, [pos[target[i]] for i in idx_t]]
        obs = ~np.isnan(Xs)
        mu, sd = np.nanmean(Xs, 0), np.nanstd(Xs, 0)
        sd = np.where(sd > 1e-6, sd, 1.0)
        Z = np.where(obs, (Xs - mu) / sd, 0.0)
        O = obs.astype(float)
        cnt = O.T @ O
        r = np.clip((Z.T @ Z) / np.maximum(cnt, 1), -0.999, 0.999)
        ok = cnt >= min_overlap
        z = np.arctanh(r)
        w = np.where(ok, cnt, 0.0)
        ix = np.ix_(idx_t, idx_t)
        zsum[ix] += np.where(ok, z * w, 0.0)
        wsum[ix] += w
        nds[ix] += ok.astype(int)
    with np.errstate(invalid="ignore", divide="ignore"):
        R = np.where(wsum > 0, np.tanh(zsum / wsum), np.nan)
    np.fill_diagonal(R, np.nan)
    return R, nds


def external_graph(var_names, R: np.ndarray, n_edges: int, min_datasets: int = 1, nds=None) -> nx.Graph:
    """'More data alone' graph: the n_edges most positively co-varying pairs in the external corpus."""
    names = list(var_names)
    C = np.where(np.isnan(R), -np.inf, R)
    if nds is not None:
        C = np.where(nds >= min_datasets, C, -np.inf)
    iu = np.triu_indices_from(C, 1)
    vals = C[iu]
    top = np.argpartition(-vals, min(n_edges, len(vals) - 1))[:n_edges]
    g = nx.Graph()
    g.add_nodes_from(names)
    for t in top:
        if np.isfinite(vals[t]) and vals[t] > 0:
            g.add_edge(names[iu[0][t]], names[iu[1][t]], weight=1.0)
    g.graph["provenance"] = {"source": "external pooled co-variation", "version": "corpus", "url": "-", "sha256": "-"}
    return g


def gate_by_external(graph: nx.Graph, var_names, R: np.ndarray, power: float = 1.0) -> nx.Graph:
    """Curated edges reweighted by external co-variation: w' = w * max(0, r_ext)**power (edges with no external
    evidence or r <= 0 are dropped). Analogy: a prior updated by independent evidence."""
    pos = {n: i for i, n in enumerate(var_names)}
    g = nx.Graph()
    g.add_nodes_from(graph.nodes)
    for u, v, w in graph.edges(data="weight", default=1.0):
        r = R[pos[u], pos[v]] if u in pos and v in pos else np.nan
        if np.isfinite(r) and r > 0:
            g.add_edge(u, v, weight=float(w * r ** power))
    g.graph["provenance"] = {**graph.graph.get("provenance", {}), "gated_by": "external corpus"}
    return g
