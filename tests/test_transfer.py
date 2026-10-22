"""Synthetic checks for transfer strategies (no real data, no benchmark outcomes)."""
import numpy as np

from scp_graphfs_mcp import transfer as T


def _world(seed=0, p=120, r=5, n_ref=800, n_t=30, miss=0.4):
    rng = np.random.default_rng(seed)
    V = rng.normal(size=(p, r))
    ref = rng.normal(size=(n_ref, r)) @ V.T + 0.3 * rng.normal(size=(n_ref, p))
    ref[rng.random(ref.shape) < 0.5] = np.nan
    X = rng.normal(size=(n_t, r)) @ V.T + 0.3 * rng.normal(size=(n_t, p)) + rng.normal(size=p)
    M = rng.random(X.shape) < miss
    Xm = X.copy()
    Xm[M] = np.nan
    return ref, X, Xm, M


def _rm(Y, X, M):
    return float(np.sqrt(np.mean((Y[M] - X[M]) ** 2)))


def test_projection_beats_column_mean_and_null():
    ref, X, Xm, M = _world()
    V, warm = T.fit_loadings(T._z(ref), rank=5)
    base = np.where(np.isnan(Xm), np.nanmean(Xm, 0), Xm)
    good = _rm(T.project(Xm, V, warm, base), X, M)
    null = _rm(T.project(Xm, T.permute_rows(V, warm, 0), warm, base), X, M)
    assert good < 0.7 * _rm(base, X, M) and good < 0.7 * null


def test_coldstart_uses_warm_neighbours():
    V = np.arange(12, dtype=float).reshape(4, 3)
    warm = np.array([True, True, False, False])
    nbrs = [(np.zeros(0, int), np.zeros(0))] * 2 + [(np.array([0, 1]), np.array([1.0, 1.0])), (np.array([3]), np.array([1.0]))]
    V2, usable = T.coldstart(V, warm, nbrs)
    assert np.allclose(V2[2], (V[0] + V[1]) / 2) and usable.tolist() == [True, True, True, False]


def test_donor_knn_finite_and_keeps_observed():
    ref, X, Xm, M = _world(1)
    base = np.where(np.isnan(Xm), np.nanmean(Xm, 0), Xm)
    Y = T.donor_knn(Xm, T._z(ref), base)
    assert np.isfinite(Y).all() and np.allclose(Y[~M], X[~M])
