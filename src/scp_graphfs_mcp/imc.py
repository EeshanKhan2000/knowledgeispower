"""Inductive matrix completion with protein side information (EXPLORATION.md Amendment 5).

z-score X per protein; fit X ≈ U Vᵀ on observed entries with V = F W + Δ:
  - F (p x d): knowledge-derived protein features (scp_graphfs_mcp.features)
  - W (d x r): shared map from features to loadings (light penalty lam_w)
  - Δ (p x r): protein-specific deviation (heavy penalty lam_delta) -> the prior dominates when data are scarce
Optional V0 (p x r'): pretrained loadings appended to F. Adam, fixed seed. Only NaN entries are filled.
"""

from __future__ import annotations

import numpy as np


def imc(X, F, rank: int = 10, lam_u: float = 1.0, lam_w: float = 0.1, lam_delta: float = 10.0,
        iters: int = 400, lr: float = 0.05, seed: int = 0, full: bool = False):
    obs = ~np.isnan(X)
    mu = np.nanmean(X, axis=0)
    mu = np.where(np.isfinite(mu), mu, 0.0)
    sd = np.nanstd(X, axis=0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-6), sd, 1.0)
    Z = np.where(obs, (X - mu) / sd, 0.0)
    n, p = X.shape
    F = np.asarray(F, float)
    d = F.shape[1]
    rng = np.random.default_rng(seed)
    U = rng.normal(0, 0.1, (n, rank))
    W = rng.normal(0, 0.1 / max(np.sqrt(d), 1), (d, rank))
    D = np.zeros((p, rank))
    params = [U, W, D]
    m = [np.zeros_like(x) for x in params]
    v = [np.zeros_like(x) for x in params]
    b1, b2, eps = 0.9, 0.999, 1e-8
    nobs = max(obs.sum(), 1)
    for t in range(1, iters + 1):
        V = F @ W + D
        E = np.where(obs, U @ V.T - Z, 0.0)
        gU = (E @ V) / nobs * n + lam_u * U / p
        gV = (E.T @ U) / nobs * n
        gW = F.T @ gV + lam_w * W / p
        gD = gV + lam_delta * D / p
        for i, g in enumerate((gU, gW, gD)):
            m[i] = b1 * m[i] + (1 - b1) * g
            v[i] = b2 * v[i] + (1 - b2) * g ** 2
            params[i] -= lr * (m[i] / (1 - b1 ** t)) / (np.sqrt(v[i] / (1 - b2 ** t)) + eps)
        U, W, D = params
    rec = mu + sd * (U @ (F @ W + D).T)
    if full:
        return rec
    out = X.copy()
    out[~obs] = rec[~obs]
    return out


def permuted_features(F, seed: int) -> np.ndarray:
    """Null: shuffle feature rows across proteins (keeps the feature distribution, breaks protein identity)."""
    return np.asarray(F)[np.random.default_rng(seed).permutation(F.shape[0])]
