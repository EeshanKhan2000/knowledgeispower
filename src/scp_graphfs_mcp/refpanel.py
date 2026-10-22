"""Reference-panel regression (RPR) imputation (EXPLORATION.md Amendment 9).

Analogy: genotype imputation. A small target study borrows *which variants predict which* (linkage disequilibrium)
from a large reference panel instead of learning it from its own few samples. Here a protein representation
(a knowledge graph, a feature embedding, or a deep bulk proteomics atlas) says which proteins predict a given
protein; the target data only calibrates one slope per protein.

For a protein j with neighbours N_j and weights w_jk (from the representation):
    s_ij  = sum_k w_jk z_ik / sum_k |w_jk|           (z = target z-scores; kNN-filled where unobserved)
    b_j   = sum_i z_ij s_ij / (sum_i s_ij^2 + lam)   over cells where j is observed (ridge-shrunk slope)
    x_ij  = mu_j + sd_j * b_j * s_ij
`stack_with_base` then mixes RPR with the kNN fill, choosing the weight by an inner validation mask taken from
the *observed* entries only (no access to held-out truth).
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from . import phase2 as P


def neighbours_from_graph(G: nx.Graph, var_names, m: int = 20) -> list[tuple[np.ndarray, np.ndarray]]:
    """Top-m neighbours by edge weight for each var_name (positions into var_names)."""
    pos = {v: i for i, v in enumerate(var_names)}
    out = []
    for v in var_names:
        nb = []
        if v in G:
            for u, d in G[v].items():
                if u != v and u in pos:
                    nb.append((float(d.get("weight", 1.0)), pos[u]))
        nb.sort(reverse=True)
        nb = nb[:m]
        out.append((np.array([j for _, j in nb], int), np.array([w for w, _ in nb], float)))
    return out


def neighbours_from_features(F: np.ndarray, m: int = 20) -> list[tuple[np.ndarray, np.ndarray]]:
    """Top-m cosine neighbours among proteins that have a representation (last column of F = has-data flag)."""
    has = F[:, -1] > 0.5
    M = F[:, :-1]
    Mn = M / np.maximum(np.linalg.norm(M, axis=1, keepdims=True), 1e-9)
    out = []
    idx = np.where(has)[0]
    S = Mn[idx] @ Mn[idx].T
    np.fill_diagonal(S, -np.inf)
    row_of = {j: r for r, j in enumerate(idx)}
    for j in range(len(F)):
        if not has[j]:
            out.append((np.zeros(0, int), np.zeros(0)))
            continue
        s = S[row_of[j]]
        top = np.argsort(-s)[:m]
        keep = s[top] > 0
        out.append((idx[top[keep]], s[top[keep]]))
    return out


def neighbours_from_data(X: np.ndarray, m: int = 20, min_overlap: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
    """Data-only control: top-m partners by pairwise-complete correlation in the target matrix itself."""
    obs = ~np.isnan(X)
    mu, sd = np.nanmean(X, 0), np.nanstd(X, 0)
    sd = np.where(sd > 1e-6, sd, 1.0)
    Z = np.where(obs, (X - np.nan_to_num(mu)) / sd, 0.0)
    O = obs.astype(float)
    n = O.T @ O
    C = (Z.T @ Z) / np.maximum(n, 1)
    C[n < min_overlap] = 0.0
    np.fill_diagonal(C, -np.inf)
    out = []
    for j in range(X.shape[1]):
        top = np.argsort(-C[j])[:m]
        keep = C[j, top] > 0
        out.append((top[keep], C[j, top[keep]]))
    return out


def neighbours_from_reference(R: np.ndarray, has: np.ndarray, m: int = 20, min_overlap: int = 30,
                              lam: float = 1.0) -> list[tuple[np.ndarray, np.ndarray]]:
    """Reference-panel (bulk atlas) neighbours with ridge regression coefficients computed *in the reference*.

    R is (p x L), standardised per protein with NaN where unmeasured. Returns, per protein, the top-m partners by
    |corr| and the ridge coefficients beta = (C_NN + lam I)^-1 C_Nj (correlation scale)."""
    obs = ~np.isnan(R)
    Z = np.where(obs, R, 0.0)
    O = obs.astype(float)
    n = O @ O.T
    C = (Z @ Z.T) / np.maximum(n, 1)
    C[n < min_overlap] = 0.0
    C[~has, :] = 0.0
    C[:, ~has] = 0.0
    np.fill_diagonal(C, 0.0)
    out = []
    for j in range(R.shape[0]):
        if not has[j]:
            out.append((np.zeros(0, int), np.zeros(0)))
            continue
        top = np.argsort(-np.abs(C[j]))[:m]
        top = top[np.abs(C[j, top]) > 0]
        if not len(top):
            out.append((top, np.zeros(0)))
            continue
        A = C[np.ix_(top, top)].copy()
        np.fill_diagonal(A, 1.0)
        beta = np.linalg.solve(A + lam * np.eye(len(top)), C[top, j])
        out.append((top, beta))
    return out


def permute_neighbours(nbrs, seed: int):
    """Null: relabel proteins at random. Keeps each neighbour list's size and weights, breaks protein identity."""
    p = len(nbrs)
    perm = np.random.default_rng(seed).permutation(p)  # protein j takes the neighbour list of protein perm[j]
    inv = np.argsort(perm)
    out = []
    for j in range(p):
        idx, w = nbrs[perm[j]]
        out.append((inv[idx] if len(idx) else idx, w))
    return out


def rpr(Xm: np.ndarray, nbrs, base: np.ndarray | None = None, lam: float = 10.0, signed: bool = False) -> np.ndarray:
    """Reference-panel regression. Unobserved entries of Xm are predicted; observed ones are returned unchanged.

    signed=False: weights are similarities (neighbour average). signed=True: weights are regression coefficients
    (from `neighbours_from_reference`), used as given."""
    obs = ~np.isnan(Xm)
    if base is None:
        base = P._fill(Xm, P.loo_knn(Xm))
    mu = np.nanmean(Xm, 0)
    sd = np.nanstd(Xm, 0)
    mu = np.where(np.isfinite(mu), mu, np.nanmean(base, 0))
    sd = np.where(np.isfinite(sd) & (sd > 1e-6), sd, 1.0)
    Z = (np.where(obs, Xm, base) - mu) / sd
    out = base.copy()
    for j in np.where((~obs).any(0))[0]:
        idx, w = nbrs[j]
        if not len(idx):
            continue
        s = Z[:, idx] @ w / (1.0 if signed else max(np.abs(w).sum(), 1e-9))
        o = obs[:, j]
        if o.sum() < 3:
            continue
        b = float(Z[o, j] @ s[o] / (s[o] @ s[o] + lam))
        miss = ~o
        out[miss, j] = mu[j] + sd[j] * b * s[miss]
    return out


def stack_with_base(Xm: np.ndarray, make_other, inner_frac: float = 0.1, seed: int = 0,
                    grid=(0.0, 0.25, 0.5, 0.75, 1.0), eligible: np.ndarray | None = None):
    """Mix the kNN fill with another imputer: w*kNN + (1-w)*other, w picked on an inner mask of *observed* entries.

    make_other(Xm, base) -> filled matrix. Returns (filled, chosen_w)."""
    rng = np.random.default_rng(seed + 7919)
    obs = ~np.isnan(Xm)
    if eligible is not None:
        obs = obs & eligible[None, :]
    cand = np.argwhere(obs)
    pick = cand[rng.choice(len(cand), max(1, int(inner_frac * len(cand))), replace=False)]
    Xi = Xm.copy()
    Xi[pick[:, 0], pick[:, 1]] = np.nan
    bi = P._fill(Xi, P.loo_knn(Xi))
    oi = make_other(Xi, bi)
    t = Xm[pick[:, 0], pick[:, 1]]
    a, b = bi[pick[:, 0], pick[:, 1]], oi[pick[:, 0], pick[:, 1]]
    errs = [float(np.mean((w * a + (1 - w) * b - t) ** 2)) for w in grid]
    w = grid[int(np.argmin(errs))]
    base = P._fill(Xm, P.loo_knn(Xm))
    other = make_other(Xm, base)
    return w * base + (1 - w) * other, w
