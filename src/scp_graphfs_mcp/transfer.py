"""Transfer strategies for tiny targets (EXPLORATION.md Amendment 10).

Cross-domain analogies:
- **Reference projection** (ancestry PCA / recommender cold-start / a linear masked auto-encoder pretrained elsewhere):
  protein loadings V are learned on a large *external* reference (other single-cell datasets, optionally bulk
  proteomics panels); the few target cells only fit their own scores u_i. Proteins the reference never saw get V from
  their knowledge-graph neighbours (the curated prior enters exactly where data cannot).
- **Reference donors** (genotype imputation copies from reference haplotypes): external cells join the kNN donor pool.

All references exclude the target (leave-one-dataset-out) and never contain holdouts.
"""

from __future__ import annotations

import numpy as np

from .external import CORPUS, HOLDOUTS, _load
from .ids import group_accessions


def _target_accs(var_names):
    return [(group_accessions(f) or [""])[0] for f in var_names]


def _z(X):
    mu, sd = np.nanmean(X, 0), np.nanstd(X, 0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-6), sd, 1.0)
    return (X - mu) / sd


def corpus_reference(var_names, exclude: tuple[str, ...]) -> np.ndarray:
    """External single cells aligned to var_names: (N_cells x p), z-scored per protein *within* each dataset."""
    if set(exclude) & HOLDOUTS:
        raise ValueError("holdouts are never part of the corpus")
    target = _target_accs(var_names)
    blocks = []
    for name in CORPUS:
        if name in exclude:
            continue
        X, accs = _load(name)
        pos = {a: i for i, a in enumerate(accs)}
        B = np.full((X.shape[0], len(target)), np.nan)
        cols = [(j, pos[a]) for j, a in enumerate(target) if a in pos]
        if cols:
            tj, sj = zip(*cols)
            B[:, list(tj)] = X[:, list(sj)]
        blocks.append(_z(B))
    return np.vstack(blocks)


def bulk_reference(var_names) -> np.ndarray:
    """CCLE + ProteomeHD samples aligned to var_names, (N_samples x p), z-scored per protein (NaN = absent)."""
    from .reps import ccle, proteomehd

    out = []
    for m in (ccle, proteomehd):
        R, has = m.reference(var_names)
        R = np.where(np.asarray(has, bool)[:, None], R, np.nan)
        out.append(_z(R.T))
    return np.vstack(out)


def fit_loadings(Zref: np.ndarray, rank: int = 20, lam: float = 5.0, iters: int = 15, min_obs: int = 20,
                 seed: int = 0):
    """Masked low-rank factorisation Zref ~ U V^T by alternating ridge. Returns (V, warm) with V (p x rank);
    proteins observed in < min_obs reference samples are 'cold' (warm=False, V row = 0)."""
    obs = ~np.isnan(Zref)
    warm = obs.sum(0) >= min_obs
    Z = np.where(obs, Zref, 0.0)[:, warm]
    O = obs[:, warm]
    keep = O.sum(1) >= rank
    Z, O = Z[keep], O[keep]
    rng = np.random.default_rng(seed)
    V = 0.1 * rng.normal(size=(Z.shape[1], rank))
    U = np.zeros((Z.shape[0], rank))
    I = lam * np.eye(rank)
    for _ in range(iters):
        for i in range(Z.shape[0]):
            o = O[i]
            Vo = V[o]
            U[i] = np.linalg.solve(Vo.T @ Vo + I, Vo.T @ Z[i, o])
        for j in range(Z.shape[1]):
            o = O[:, j]
            Uo = U[o]
            V[j] = np.linalg.solve(Uo.T @ Uo + I, Uo.T @ Z[o, j])
    Vfull = np.zeros((Zref.shape[1], rank))
    Vfull[warm] = V
    return Vfull, warm


def coldstart(V: np.ndarray, warm: np.ndarray, nbrs) -> tuple[np.ndarray, np.ndarray]:
    """Give each cold protein the weighted mean loading of its *warm* knowledge neighbours (nbrs: list of
    (idx, weights) as in refpanel). Returns (V', usable mask)."""
    V2 = V.copy()
    usable = warm.copy()
    for j in np.where(~warm)[0]:
        idx, w = nbrs[j]
        if not len(idx):
            continue
        ok = warm[idx]
        if not ok.any():
            continue
        ww = np.abs(w[ok])
        V2[j] = (ww[:, None] * V[idx[ok]]).sum(0) / max(ww.sum(), 1e-9)
        usable[j] = True
    return V2, usable


def project(Xm: np.ndarray, V: np.ndarray, usable: np.ndarray, base: np.ndarray, lam: float = 5.0) -> np.ndarray:
    """Fit each target cell's scores on its observed, usable proteins; predict unobserved usable entries.
    Entries of unusable proteins keep `base` (the kNN fill)."""
    obs = ~np.isnan(Xm)
    mu = np.nanmean(Xm, 0)
    sd = np.nanstd(Xm, 0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-6), sd, 1.0)
    Z = np.where(obs, (Xm - np.nan_to_num(mu)) / sd, 0.0)
    out = base.copy()
    I = lam * np.eye(V.shape[1])
    ok_col = usable & np.isfinite(mu)
    for i in range(Xm.shape[0]):
        o = obs[i] & ok_col
        if o.sum() < 3:
            continue
        u = np.linalg.solve(V[o].T @ V[o] + I, V[o].T @ Z[i, o])
        miss = ~obs[i] & ok_col
        out[i, miss] = mu[miss] + sd[miss] * (V[miss] @ u)
    return out


def permute_rows(V: np.ndarray, warm: np.ndarray, seed: int):
    """Null: shuffle which protein gets which loading (among warm proteins). Keeps the reference's spectrum,
    breaks protein identity."""
    V2 = V.copy()
    idx = np.where(warm)[0]
    V2[idx] = V[np.random.default_rng(seed).permutation(idx)]
    return V2


def donor_knn(Xm: np.ndarray, Zref: np.ndarray, base: np.ndarray, k: int = 10, n_donors: int = 2000,
              seed: int = 0) -> np.ndarray:
    """Reference-donor kNN: donors = external cells (z-space, mapped to target scale with target mu/sd).
    Distance = mean squared z-difference over co-observed proteins (>= 20)."""
    obs = ~np.isnan(Xm)
    mu = np.nanmean(Xm, 0)
    sd = np.nanstd(Xm, 0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-6), sd, 1.0)
    Z = np.where(obs, (Xm - np.nan_to_num(mu)) / sd, np.nan)
    rng = np.random.default_rng(seed)
    R = Zref[rng.choice(len(Zref), min(n_donors, len(Zref)), replace=False)]
    Ro = ~np.isnan(R)
    R0 = np.where(Ro, R, 0.0)
    out = base.copy()
    for i in range(Xm.shape[0]):
        o = obs[i]
        zi = np.where(o, Z[i], 0.0)
        cnt = Ro[:, o].sum(1)
        d = ((R0[:, o] - zi[o]) ** 2 * Ro[:, o]).sum(1) / np.maximum(cnt, 1)
        d = np.where(cnt >= 20, d, np.inf)
        for j in np.where(~o & np.isfinite(mu))[0]:
            has = Ro[:, j] & np.isfinite(d)
            if has.sum() < k:
                continue
            nn = np.argsort(np.where(has, d, np.inf))[:k]
            out[i, j] = mu[j] + sd[j] * R[nn, j].mean()
    return out
