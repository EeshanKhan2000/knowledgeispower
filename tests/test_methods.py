"""Core methods: imputation only fills NaN, uses partners, propagation is a proper RWR."""
import networkx as nx
import numpy as np
import pytest

from scp_graphfs_mcp.datasets import from_log2_matrix
from scp_graphfs_mcp.methods import impute_with_prior, propagate, select_features, select_random


def _graph(nodes, edges):
    g = nx.Graph(); g.add_nodes_from(nodes); g.add_edges_from(edges, weight=1.0)
    g.graph["provenance"] = {"source": "toy", "version": "0", "url": "-", "sha256": "-"}
    return g


@pytest.fixture
def stoich():
    """P0..P2 form a 'complex' sharing one latent abundance; P3, P4 independent."""
    rng = np.random.default_rng(1)
    latent = rng.normal(0, 1, 200)
    X = np.column_stack([10 + latent + rng.normal(0, .1, 200) for _ in range(3)]
                        + [rng.normal(8, 1, 200) for _ in range(2)])
    truth = X.copy()
    X[rng.random(X.shape) < 0.1] = np.nan
    names = [f"P{i}" for i in range(5)]
    return from_log2_matrix(X, [f"c{i}" for i in range(200)], names), truth, _graph(names, [("P0", "P1"), ("P1", "P2"), ("P0", "P2")])


def test_only_nan_entries_change(stoich):
    a, _, g = stoich
    out = impute_with_prior(a, g)
    X = np.asarray(a.X)
    obs = ~np.isnan(X)
    assert np.array_equal(out.X[obs], X[obs]) and not np.isnan(out.X).any()
    assert out.uns["impute_with_prior"]["n_missing"] == int((~obs).sum())


def test_partners_beat_knn_on_true_complex(stoich):
    a, truth, g = stoich
    miss = np.isnan(np.asarray(a.X))
    cols = np.zeros_like(miss); cols[:, :3] = True
    m = miss & cols
    prior = impute_with_prior(a, g).X
    knn = impute_with_prior(a, _graph(list(a.var_names), [])).X  # no edges -> pure kNN fallback
    rmse = lambda Y: np.sqrt(np.mean((Y[m] - truth[m]) ** 2))
    assert rmse(prior) < rmse(knn)
    assert 0.8 < impute_with_prior(a, g).uns["impute_with_prior"]["beta"] < 1.2


def test_rwr_sums_to_one_and_spreads():
    g = _graph(list("abcd"), [("a", "b"), ("b", "c")])
    p = propagate(g, {"a": 1.0}, list("abcd"), alpha=0.5)
    assert abs(p.sum() - 1) < 1e-8 and p[1] > 0 and p[2] > 0 and p[3] == 0
    with pytest.raises(ValueError):
        propagate(g, {"a": -1.0}, list("abcd"))


def test_selection_modes(stoich):
    a, _, g = stoich
    assert len(select_features(a, None, 2, "none")) == 2
    assert len(select_features(a, g, 2, "soft_weight")) == 2
    assert select_random(a, 2, 0) == select_random(a, 2, 0)
    with pytest.raises(ValueError):
        select_features(a, g, 2, "bogus")
