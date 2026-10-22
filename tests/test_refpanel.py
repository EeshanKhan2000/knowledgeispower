"""Synthetic checks for reference-panel regression (no real data, no benchmark outcomes)."""
import numpy as np

from scp_graphfs_mcp import refpanel as R


def _toy(seed=0, n=30, groups=40, size=5, miss=0.3):
    rng = np.random.default_rng(seed)
    f = rng.normal(size=(n, groups))
    X = np.repeat(f, size, axis=1) + 0.3 * rng.normal(size=(n, groups * size)) + rng.normal(size=groups * size)
    M = rng.random(X.shape) < miss
    Xm = X.copy()
    Xm[M] = np.nan
    nbrs = [(np.array([g * size + k for k in range(size) if g * size + k != j]), np.ones(size - 1))
            for j in range(groups * size) for g in [j // size]]
    return X, Xm, M, nbrs


def test_rpr_true_neighbours_beat_permuted_null():
    X, Xm, M, nbrs = _toy()
    rm = lambda Y: np.sqrt(np.mean((Y[M] - X[M]) ** 2))  # noqa: E731
    good = rm(R.rpr(Xm, nbrs))
    null = rm(R.rpr(Xm, R.permute_neighbours(nbrs, 0)))
    assert good < 0.8 * null


def test_rpr_keeps_observed_and_fills_all():
    X, Xm, M, nbrs = _toy(1)
    Y = R.rpr(Xm, nbrs)
    assert np.allclose(Y[~M], X[~M]) and np.isfinite(Y).all()


def test_permute_neighbours_preserves_sizes():
    _, _, _, nbrs = _toy()
    P = R.permute_neighbours(nbrs, 3)
    assert sorted(len(i) for i, _ in P) == sorted(len(i) for i, _ in nbrs)


def test_reference_neighbours_recover_groups():
    rng = np.random.default_rng(2)
    f = rng.normal(size=(200, 10))
    Rf = np.repeat(f, 4, axis=1).T + 0.3 * rng.normal(size=(40, 200))
    Rf = (Rf - Rf.mean(1, keepdims=True)) / Rf.std(1, keepdims=True)
    nb = R.neighbours_from_reference(Rf, np.ones(40, bool), m=3)
    assert all(set(idx) == {g * 4 + k for k in range(4)} - {j} for j, (idx, _) in enumerate(nb) for g in [j // 4])


def test_stack_with_base_returns_weight_in_grid():
    X, Xm, M, nbrs = _toy(4)
    Y, w = R.stack_with_base(Xm, lambda Xi, b: R.rpr(Xi, nbrs, base=b))
    assert w in (0.0, 0.25, 0.5, 0.75, 1.0) and np.isfinite(Y).all()
