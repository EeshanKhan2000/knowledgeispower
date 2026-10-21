"""Prior-guided imputation, network propagation and panel selection (see
``benchmarks/PREREGISTRATION.md`` for the exact settings used in the benchmark)."""

from __future__ import annotations

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scp_prep import check_resources
from scp_prep.impute import impute_knn

from .registry import METHODS, register_method


# --------------------------------------------------------------------------- helpers


def _X(adata) -> np.ndarray:
    return np.asarray(adata.X, dtype=float)


def adjacency(graph: nx.Graph, var_names) -> sp.csr_matrix:
    """Weighted adjacency in ``var_names`` order (nodes absent from the graph get no edges)."""
    names = list(var_names)
    pos = {n: i for i, n in enumerate(names)}
    rows, cols, vals = [], [], []
    for u, v, w in graph.edges(data="weight", default=1.0):
        if u in pos and v in pos:
            rows += [pos[u], pos[v]]
            cols += [pos[v], pos[u]]
            vals += [w, w]
    n = len(names)
    return sp.csr_matrix((vals, (rows, cols)), shape=(n, n))


def zscore_stats(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-6), sd, 1.0)
    return np.where(np.isfinite(mu), mu, 0.0), sd


def knn_fill(adata, n_neighbors: int = 10) -> np.ndarray:
    """kNN-imputed X via scp-prep (k=10, uniform)."""
    return _X(impute_knn(adata, n_neighbors=n_neighbors, inplace=False))


# --------------------------------------------------------------------------- imputation


def partner_zscores(X: np.ndarray, W: sp.csr_matrix):
    """Edge-weighted mean of observed partners' z-scores, per cell x protein.

    Returns ``(zhat, support, mu, sd)``; ``support`` = summed weight of observed partners
    (0 where a protein has no observed partner in that cell).
    """
    mu, sd = zscore_stats(X)
    obs = ~np.isnan(X)
    Z0 = np.where(obs, (X - mu) / sd, 0.0)
    num = np.asarray((sp.csr_matrix(Z0) @ W).todense())
    support = np.asarray((sp.csr_matrix(obs.astype(float)) @ W).todense())
    with np.errstate(invalid="ignore", divide="ignore"):
        zhat = np.where(support > 0, num / support, 0.0)
    return zhat, support, mu, sd


def fit_beta(X: np.ndarray, zhat: np.ndarray, support: np.ndarray, mu, sd) -> float:
    """One scalar per graph: least squares of observed z on partner-predicted z (no intercept)."""
    obs = ~np.isnan(X) & (support > 0)
    if not obs.any():
        return 0.0
    z = ((X - mu) / sd)[obs]
    p = zhat[obs]
    denom = float(p @ p)
    return float(z @ p / denom) if denom > 0 else 0.0


def impute_with_prior(adata, graph: nx.Graph, *, fallback: np.ndarray | None = None,
                      n_neighbors: int = 10):
    """Fill NaNs in ``X`` from observed co-complex partners in the same cell; kNN where none.

    Returns a copy with ``X`` filled, ``layers['was_imputed']`` and
    ``layers['imputed_by_prior']`` (bool), and ``uns['impute_with_prior']`` (report).
    ``fallback`` may pass a precomputed kNN-filled matrix to avoid recomputation.
    """
    check_resources(shape=(adata.n_obs, adata.n_vars * 4), itemsize=8, hard=True, op="impute_with_prior")
    X = _X(adata)
    W = adjacency(graph, adata.var_names)
    zhat, support, mu, sd = partner_zscores(X, W)
    beta = fit_beta(X, zhat, support, mu, sd)
    miss = np.isnan(X)
    by_prior = miss & (support > 0)
    fb = fallback if fallback is not None else knn_fill(adata, n_neighbors)
    out_X = X.copy()
    out_X[by_prior] = (mu + sd * beta * zhat)[by_prior]
    rest = miss & ~by_prior
    out_X[rest] = fb[rest]
    out = adata.copy()
    out.X = out_X
    out.layers["was_imputed"] = miss
    out.layers["imputed_by_prior"] = by_prior
    out.uns["impute_with_prior"] = {
        "beta": beta,
        "n_missing": int(miss.sum()),
        "n_imputed_by_prior": int(by_prior.sum()),
        "n_imputed_by_knn_fallback": int(rest.sum()),
        "prior": dict(graph.graph.get("provenance", {})),
    }
    return out


def impute_mean(adata) -> np.ndarray:
    X = _X(adata)
    mu, _ = zscore_stats(X)
    return np.where(np.isnan(X), mu, X)


# --------------------------------------------------------------------------- propagation


def propagate(graph: nx.Graph, scores: dict | np.ndarray, var_names=None, alpha: float = 0.5,
              tol: float = 1e-10, max_iter: int = 1000) -> np.ndarray:
    """Random walk with restart: ``p = (1-alpha) W p + alpha s`` (alpha = restart probability).

    ``W`` is the column-normalised weighted adjacency; dangling nodes keep their own mass
    (self-loop). ``s`` is the non-negative score vector normalised to sum 1.
    """
    if not 0 < alpha <= 1:
        raise ValueError("alpha (restart probability) must be in (0, 1]")
    names = list(var_names) if var_names is not None else list(graph.nodes)
    if isinstance(scores, dict):
        s = np.array([float(scores.get(n, 0.0)) for n in names])
    else:
        s = np.asarray(scores, dtype=float)
    if (s < 0).any() or not np.isfinite(s).all():
        raise ValueError("scores must be finite and non-negative")
    s = s / s.sum() if s.sum() > 0 else np.full(len(s), 1 / len(s))
    A = adjacency(graph, names)
    deg = np.asarray(A.sum(axis=0)).ravel()
    dangling = deg == 0
    Wn = A @ sp.diags(np.where(dangling, 0.0, 1.0 / np.where(dangling, 1.0, deg)))
    p = s.copy()
    for _ in range(max_iter):
        p_new = (1 - alpha) * (Wn @ p + dangling * p) + alpha * s
        if np.abs(p_new - p).sum() < tol:
            return p_new
        p = p_new
    return p


# --------------------------------------------------------------------------- selection


def candidates(adata, min_detection: float = 0.8) -> np.ndarray:
    return (~np.isnan(_X(adata))).mean(axis=0) >= min_detection


def hvp_scores(adata, min_detection: float = 0.8) -> np.ndarray:
    """Variance of observed log2 values; 0 for non-candidates."""
    X = _X(adata)
    var = np.nan_to_num(np.nanvar(X, axis=0))
    return np.where(candidates(adata, min_detection), var, 0.0)


def _top_k(score: np.ndarray, mask: np.ndarray, var_names, k: int) -> list[str]:
    s = np.where(mask, score, -np.inf)
    order = np.lexsort((np.arange(len(s)), -s))  # stable: ties broken by position
    return [var_names[i] for i in order[:k] if np.isfinite(s[i])]


def select_features(adata, graph: nx.Graph | None, k: int, mode: str = "soft_weight",
                    alpha: float = 0.5, min_detection: float = 0.8, return_scores: bool = False):
    """Choose a k-protein panel.

    * ``none``: top-k highly variable proteins (HVP) among candidates (detected in >= 80% of cells).
    * ``soft_weight``: RWR (restart ``alpha``) of the HVP scores over ``graph``, top-k candidates.
    * ``hard_filter``: owned by Collaborator A; dispatches to ``METHODS['hard_filter'].select``
      if registered (``contrib/hard_filter``), else raises ``NotImplementedError``.
    """
    names = list(adata.var_names)
    cand = candidates(adata, min_detection)
    base = hvp_scores(adata, min_detection)
    if mode == "none":
        score = base
    elif mode == "soft_weight":
        if graph is None:
            raise ValueError("soft_weight needs a graph")
        score = propagate(graph, base, names, alpha=alpha)
    elif mode == "hard_filter":
        if "hard_filter" not in METHODS or METHODS["hard_filter"].select is None:
            raise NotImplementedError(
                "hard_filter is not registered; see contrib/hard_filter/README.md (Collaborator A's arm)")
        panel = list(METHODS["hard_filter"].select(adata, graph, k))
        return (panel, None) if return_scores else panel
    else:
        raise ValueError(f"unknown mode {mode!r}; use 'none', 'soft_weight' or 'hard_filter'")
    panel = _top_k(score, cand, names, k)
    return (panel, score) if return_scores else panel


def select_random(adata, k: int, seed: int, min_detection: float = 0.8) -> list[str]:
    names = np.array(adata.var_names)[candidates(adata, min_detection)]
    return list(np.random.default_rng(seed).choice(names, size=min(k, len(names)), replace=False))


register_method("prior_impute", "Partner-weighted z-score imputation with kNN fallback",
                impute=impute_with_prior, contrib=False)
register_method("soft_weight", "RWR-propagated HVP scores, top-k",
                select=lambda a, g, k: select_features(a, g, k, "soft_weight"), contrib=False)
register_method("hvp", "Top-k highly variable proteins (no prior)",
                select=lambda a, g, k: select_features(a, None, k, "none"), contrib=False)
