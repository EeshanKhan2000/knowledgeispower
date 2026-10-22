"""Shared machinery for *bulk co-regulation reference panels* (ccle, proteomehd). Not a representation itself.

A reference panel is a (proteins x samples) matrix of bulk protein measurements from an independent study.
Analogy: a genotype-imputation reference panel says which SNPs predict which; a deep bulk proteomics atlas
says which proteins co-vary. Everything here is fit on the panel only, never on single-cell data.

Conventions (shared by every panel module):

* Alignment: a var_name (protein group ``'P1;P2-2'``) maps to the panel row of the *first* accession in the
  group (canonical, isoform suffix dropped) that the panel contains. ``features._accs`` uses only the first
  accession; trying the rest raises coverage without changing which protein a match refers to.
* Standardisation: each panel protein is z-scored over the samples where it was observed (ddof=0);
  missing stays NaN.
* ``pairwise_corr``: exact pairwise-complete Pearson r (each pair re-centred on its shared samples).
* ``svd_loadings``: SVD of the standardised panel with NaN -> 0 (i.e. missing = the protein's mean) over all
  panel proteins with >= ``min_obs`` observations. Loadings U[:, :d] * S[:d], sign fixed so each component's
  largest-|loading| entry is positive (deterministic).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import networkx as nx
import numpy as np

from ..ids import DATA_DIR, group_accessions

REPS_DIR = DATA_DIR / "cache" / "reps"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def standardise(X: np.ndarray) -> np.ndarray:
    """Row-wise z-score over observed entries (NaN kept)."""
    X = np.asarray(X, float)
    mu = np.nanmean(X, 1, keepdims=True)
    sd = np.nanstd(X, 1, keepdims=True)
    sd = np.where(np.isfinite(sd) & (sd > 1e-9), sd, 1.0)
    return (X - mu) / sd


def align(var_names, index: dict[str, int]) -> np.ndarray:
    """Panel row for each var_name (-1 when none of its accessions is in the panel)."""
    out = np.full(len(var_names), -1, int)
    for i, f in enumerate(var_names):
        for a in group_accessions(str(f)):
            if a in index:
                out[i] = index[a]
                break
    return out


def reference(var_names, X: np.ndarray, index: dict[str, int]):
    """(p x L) standardised panel rows aligned to var_names (NaN where absent) and has-mask (present)."""
    rows = align(var_names, index)
    Z = standardise(X)
    R = np.full((len(rows), X.shape[1]), np.nan)
    has = rows >= 0
    R[has] = Z[rows[has]]
    return R, has


def pairwise_corr(Xa: np.ndarray):
    """Exact pairwise-complete Pearson r between rows of Xa (NaN = missing). Returns (r, n_shared)."""
    O = (~np.isnan(Xa)).astype(float)
    X0 = np.where(O > 0, Xa, 0.0)
    n = O @ O.T
    sx = X0 @ O.T                      # sum of x_i over samples shared with j
    sxx = (X0 * X0) @ O.T
    sxy = X0 @ X0.T
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = n * sxy - sx * sx.T
        var_i = n * sxx - sx * sx
        r = cov / np.sqrt(var_i * var_i.T)
    return np.clip(r, -1.0, 1.0), n.astype(int)


def knn_graph(var_names, rows: np.ndarray, S: np.ndarray, top: int, valid: np.ndarray | None = None) -> nx.Graph:
    """Union-of-kNN graph: each aligned var_name linked to its `top` highest-S partners (S > 0, `valid` pairs,
    and partners mapped to a *different* panel row). Edge weight = S. All var_names are nodes."""
    names = [str(v) for v in var_names]
    g = nx.Graph()
    g.add_nodes_from(names)
    idx = np.flatnonzero(rows >= 0)
    if len(idx) < 2:
        return g
    C = np.array(S, float, copy=True)
    same = rows[idx][:, None] == rows[idx][None, :]
    bad = same | ~np.isfinite(C) | (C <= 0)
    if valid is not None:
        bad |= ~valid
    C[bad] = -np.inf
    k = min(top, len(idx) - 1)
    part = np.argpartition(-C, k - 1, axis=1)[:, :k] if k >= 1 else np.zeros((len(idx), 0), int)
    for a, js in enumerate(part):
        for b in js:
            w = C[a, b]
            if np.isfinite(w):
                u, v = names[idx[a]], names[idx[b]]
                if not g.has_edge(u, v):
                    g.add_edge(u, v, weight=float(w))
    return g


def svd_loadings(X: np.ndarray, d: int, min_obs: int):
    """Protein loadings of the standardised panel (NaN -> 0). Returns (L (n_panel x d), ok mask)."""
    ok = (~np.isnan(X)).sum(1) >= min_obs
    Z = np.nan_to_num(standardise(X[ok]), nan=0.0)
    U, s, _ = np.linalg.svd(Z, full_matrices=False)
    k = min(d, len(s))
    Lk = U[:, :k] * s[:k]
    sign = np.sign(Lk[np.abs(Lk).argmax(0), np.arange(k)])
    Lk = Lk * np.where(sign == 0, 1.0, sign)
    out = np.zeros((X.shape[0], k))
    out[ok] = Lk
    return out, ok
