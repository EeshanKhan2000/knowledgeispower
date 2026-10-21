"""Phase-2 exploratory methods (see benchmarks/EXPLORATION.md and GitHub issues #2-#6).

All functions take a cells x proteins log2 matrix ``X`` with NaN = missing (training entries only)
and return a fully filled matrix of the same shape; observed entries are returned unchanged.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import scipy.sparse as sp
from sklearn.metrics.pairwise import nan_euclidean_distances

from .methods import adjacency


# --------------------------------------------------------------------------- shared pieces


def loo_knn(X: np.ndarray, k: int = 10) -> np.ndarray:
    """kNN prediction for EVERY entry (observed ones leave themselves out).

    Same semantics as sklearn's KNNImputer (nan-euclidean distances, donors = cells observing
    the protein), but also predicts observed entries so residuals can be formed.
    """
    obs = ~np.isnan(X)
    D = nan_euclidean_distances(X)
    D = np.where(np.isfinite(D), D, np.inf)
    np.fill_diagonal(D, np.inf)
    order = np.argsort(D, axis=1, kind="stable")
    X0 = np.where(obs, X, 0.0)
    K = np.full(X.shape, np.nan)
    colmean = np.nanmean(X, axis=0)
    for j in range(X.shape[1]):
        donors = obs[order, j]                      # cells x neighbours (sorted), True if donor observes j
        take = donors & (np.cumsum(donors, axis=1) <= k)
        vals = X0[order, j] * take
        n = take.sum(1)
        K[:, j] = np.where(n > 0, vals.sum(1) / np.maximum(n, 1), colmean[j])
    return K


def _support(obs: np.ndarray, W: sp.csr_matrix) -> np.ndarray:
    return np.asarray((sp.csr_matrix(obs.astype(float)) @ W).todense())


def _wmean(V0: np.ndarray, obs: np.ndarray, W: sp.csr_matrix):
    num = np.asarray((sp.csr_matrix(np.where(obs, V0, 0.0)) @ W).todense())
    sup = _support(obs, W)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(sup > 0, num / sup, 0.0), sup


def _ls_beta(target, pred, mask) -> float:
    p, t = pred[mask], target[mask]
    d = float(p @ p)
    return float(t @ p / d) if d > 0 else 0.0


def _fill(X, est):
    out = X.copy()
    m = np.isnan(X)
    out[m] = est[m]
    return out


# --------------------------------------------------------------------------- E1 residual-on-kNN


def residual_on_knn(X, graph: nx.Graph, var_names, K: np.ndarray | None = None, gate: float = 0.0,
                    return_parts: bool = False):
    """x̂ = K + β · weighted mean of partners' kNN residuals (same cell). ``gate``>0 enables E4:
    each edge weight is multiplied by max(0, residual correlation)**gate (computed on training entries)."""
    obs = ~np.isnan(X)
    K = loo_knn(X) if K is None else K
    R = np.where(obs, X - K, 0.0)
    W = adjacency(graph, var_names)
    if gate > 0 and W.nnz:
        W = gated_weights(R, obs, W, gate)
    rhat, sup = _wmean(R, obs, W)
    beta = _ls_beta(R, rhat, obs & (sup > 0))
    est = K + beta * rhat
    out = _fill(X, est)
    return (out, {"beta": beta, "support": sup, "K": K}) if return_parts else out


def gated_weights(R, obs, W: sp.csr_matrix, gate: float) -> sp.csr_matrix:
    """E4: reweight existing edges by positive residual correlation (pairwise over co-observed cells)."""
    W = W.tocoo()
    n_obs = obs.astype(float)
    Rs = R - (R.sum(0) / np.maximum(n_obs.sum(0), 1)) * n_obs
    vals = []
    for i, j, w in zip(W.row, W.col, W.data):
        both = obs[:, i] & obs[:, j]
        if both.sum() < 10:
            vals.append(0.0)
            continue
        a, b = Rs[both, i], Rs[both, j]
        den = np.sqrt((a @ a) * (b @ b))
        r = (a @ b) / den if den > 0 else 0.0
        vals.append(w * max(r, 0.0) ** gate)
    return sp.csr_matrix((vals, (W.row, W.col)), shape=W.shape)


# --------------------------------------------------------------------------- E2 stoichiometric offsets


def stoich_estimate(X, graph: nx.Graph, var_names):
    """Partner estimate with slope-1 log-ratio offsets: mean_k w (x_k + median(x_j - x_k)).
    Returns (estimate, support) for every entry (estimate 0 where support 0)."""
    obs = ~np.isnan(X)
    names = list(var_names)
    pos = {n: i for i, n in enumerate(names)}
    num = np.zeros(X.shape)
    den = np.zeros(X.shape)
    X0 = np.where(obs, X, 0.0)
    for u, v, w in graph.edges(data="weight", default=1.0):
        if u not in pos or v not in pos:
            continue
        a, b = pos[u], pos[v]
        both = obs[:, a] & obs[:, b]
        if both.sum() < 5:
            continue
        delta = float(np.median(X[both, a] - X[both, b]))  # x_a ≈ x_b + delta
        for tgt, src, d in ((a, b, delta), (b, a, -delta)):
            m = obs[:, src]
            num[m, tgt] += w * (X0[m, src] + d)
            den[m, tgt] += w
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, 0.0), den


def stoich_on_knn(X, graph, var_names, K=None):
    """E2 stacked on kNN: x̂ = K + β (stoich - K_partner-consistent), β fit on training entries."""
    obs = ~np.isnan(X)
    K = loo_knn(X) if K is None else K
    S, sup = stoich_estimate(X, graph, var_names)
    D = np.where(sup > 0, S - K, 0.0)
    beta = _ls_beta(np.where(obs, X - K, 0.0), D, obs & (sup > 0))
    return _fill(X, K + beta * D)


# --------------------------------------------------------------------------- E5 inverse-variance fusion


def fused(X, graph, var_names, K=None):
    """E5: per protein, combine kNN and stoich partner estimates by inverse training error variance."""
    obs = ~np.isnan(X)
    K = loo_knn(X) if K is None else K
    S, sup = stoich_estimate(X, graph, var_names)
    eK = np.where(obs, X - K, np.nan)
    eS = np.where(obs & (sup > 0), X - S, np.nan)
    with np.errstate(all="ignore"):
        vK = np.nanmean(eK ** 2, axis=0)
        vS = np.nanmean(eS ** 2, axis=0)
    vS = np.where(np.isfinite(vS) & (np.sum(~np.isnan(eS), 0) >= 10), vS, np.inf)
    wK = 1 / np.maximum(vK, 1e-6)
    wS = np.where(np.isfinite(vS), 1 / np.maximum(vS, 1e-6), 0.0)
    est = np.where(sup > 0, (wK * K + wS * S) / (wK + wS), K)
    return _fill(X, est)


# --------------------------------------------------------------------------- E3 graph-regularised MF


def grmf(X, graph: nx.Graph | None, var_names, rank: int = 10, lam: float = 1.0, lam_g: float = 1.0,
         iters: int = 400, lr: float = 0.05, seed: int = 0, full: bool = False):
    """X ≈ mu + U Vᵀ on observed entries; penalty lam(|U|²+|V|²) + lam_g tr(Vᵀ L V) (Adam)."""
    obs = ~np.isnan(X)
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd = np.where(sd > 1e-6, sd, 1.0)
    Z = np.where(obs, (X - mu) / sd, 0.0)
    n, p = X.shape
    rng = np.random.default_rng(seed)
    U = rng.normal(0, 0.1, (n, rank))
    V = rng.normal(0, 0.1, (p, rank))
    if graph is not None and lam_g > 0:
        A = adjacency(graph, var_names)
        L = sp.diags(np.asarray(A.sum(1)).ravel()) - A
    else:
        L = None
    mU = vU = np.zeros_like(U)
    mV = vV = np.zeros_like(V)
    b1, b2, eps = 0.9, 0.999, 1e-8
    nobs = obs.sum()
    for t in range(1, iters + 1):
        E = np.where(obs, U @ V.T - Z, 0.0)
        gU = (E @ V) / nobs * n + lam * U / p
        gV = (E.T @ U) / nobs * n + lam * V / p
        if L is not None:
            gV = gV + lam_g * (L @ V) / p
        mU, vU = b1 * mU + (1 - b1) * gU, b2 * vU + (1 - b2) * gU ** 2
        mV, vV = b1 * mV + (1 - b1) * gV, b2 * vV + (1 - b2) * gV ** 2
        U = U - lr * (mU / (1 - b1 ** t)) / (np.sqrt(vU / (1 - b2 ** t)) + eps)
        V = V - lr * (mV / (1 - b1 ** t)) / (np.sqrt(vV / (1 - b2 ** t)) + eps)
    rec = mu + sd * (U @ V.T)
    return rec if full else _fill(X, rec)


def residual_on_lowrank(X, graph, var_names, base_full: np.ndarray | None = None):
    """E6: x̂ = GRMF + β · partner-weighted GRMF residuals (same cell)."""
    base = P_grmf_full(X, var_names) if base_full is None else base_full
    return residual_on_knn(X, graph, var_names, K=base)


def P_grmf_full(X, var_names):
    return grmf(X, None, var_names, lam_g=0.0, full=True)


def union_graph(a: nx.Graph, b: nx.Graph) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(a.nodes)
    for src in (a, b):
        for u, v, w in src.edges(data="weight", default=1.0):
            g.add_edge(u, v, weight=(g.edges[u, v]["weight"] if g.has_edge(u, v) else 0.0) + w)
    g.graph["provenance"] = {"source": "union", "version": "-", "url": "-", "sha256": "-"}
    return g


# --------------------------------------------------------------------------- data-derived graph


def data_graph(X, var_names, n_edges: int) -> nx.Graph:
    """'Data alone' neighbour graph: the n_edges most positively correlated protein pairs in the
    training matrix (z-scores with missing set to 0, divided by co-observed counts)."""
    obs = ~np.isnan(X)
    mu, sd = np.nanmean(X, 0), np.nanstd(X, 0)
    sd = np.where(sd > 1e-6, sd, 1.0)
    Z = np.where(obs, (X - mu) / sd, 0.0)
    O = obs.astype(float)
    cnt = O.T @ O
    C = (Z.T @ Z) / np.maximum(cnt, 1)
    C[cnt < 30] = -np.inf
    np.fill_diagonal(C, -np.inf)
    iu = np.triu_indices_from(C, 1)
    vals = C[iu]
    top = np.argpartition(-vals, n_edges)[:n_edges]
    names = list(var_names)
    g = nx.Graph()
    g.add_nodes_from(names)
    for t in top:
        if np.isfinite(vals[t]) and vals[t] > 0:
            g.add_edge(names[iu[0][t]], names[iu[1][t]], weight=1.0)
    g.graph["provenance"] = {"source": "data-derived co-variation", "version": "-", "url": "-", "sha256": "-"}
    return g


# --------------------------------------------------------------------------- W1 / P1 panel design


def keratin_mask(var_names) -> np.ndarray:
    """W1: True for protein groups containing a keratin (HGNC gene groups matching 'Keratin', from the
    committed HGNC snapshot). Keratins are the commonest sample-handling contaminants in proteomics."""
    from .ids import group_accessions, hgnc_table

    h = hgnc_table()
    kr = h[h["gene_group"].str.contains("Keratin", case=False)]
    accs = {a for ids in kr["uniprot_ids"] for a in ids.split("|") if a}
    return np.array([any(a in accs for a in group_accessions(f)) for f in var_names])


def select_coverage(X, graph: nx.Graph, var_names, k: int, exclude: np.ndarray | None = None,
                    min_detection: float = 0.8) -> list[str]:
    """P1: greedy max-coverage panel. Choosing protein p covers p and its graph neighbours; each covered
    protein counts its detection rate. Submodular → greedy is (1-1/e)-optimal. Ties: higher variance."""
    names = list(var_names)
    pos = {n: i for i, n in enumerate(names)}
    det = (~np.isnan(X)).mean(0)
    var = np.nan_to_num(np.nanvar(X, 0))
    cand = det >= min_detection
    if exclude is not None:
        cand &= ~exclude
    covers = {i: {i} | {pos[v] for v in graph.neighbors(names[i]) if v in pos} if names[i] in graph else {i}
              for i in np.where(cand)[0]}
    covered: set[int] = set()
    chosen: list[int] = []
    for _ in range(min(k, len(covers))):
        best, best_key = None, None
        for i, cov in covers.items():
            if i in chosen:
                continue
            gain = sum(det[j] for j in cov - covered)
            key = (gain, var[i])
            if best_key is None or key > best_key:
                best, best_key = i, key
        chosen.append(best)
        covered |= covers[best]
    return [names[i] for i in chosen]


def select_pivoted_qr(Xfilled, var_names, k: int, cand: np.ndarray) -> list[str]:
    """Data-only control for P1: column-subset selection by QR with column pivoting on standardised data."""
    from scipy.linalg import qr

    idx = np.where(cand)[0]
    A = Xfilled[:, idx]
    A = (A - A.mean(0)) / np.where(A.std(0) > 0, A.std(0), 1.0)
    _, _, piv = qr(A, pivoting=True, mode="economic")
    return [list(var_names)[idx[p]] for p in piv[:k]]
