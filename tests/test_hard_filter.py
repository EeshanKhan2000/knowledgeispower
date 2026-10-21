"""Acceptance tests for Collaborator A's hard_filter arm (xfail until registered)."""
import networkx as nx
import numpy as np
import pytest

from scp_graphfs_mcp.datasets import from_log2_matrix
from scp_graphfs_mcp.methods import candidates, hvp_scores, select_features
from scp_graphfs_mcp.registry import METHODS, load_contrib

load_contrib()
registered = "hard_filter" in METHODS
impl = pytest.mark.xfail(not registered, reason="hard_filter not registered yet", strict=True)


@pytest.fixture
def toy():
    rng = np.random.default_rng(0)
    X = rng.normal(10, rng.uniform(0.2, 2, 12), (40, 12))
    X[:20, 11] = np.nan  # protein 11 is not a candidate (50% detection)
    a = from_log2_matrix(X, [f"c{i}" for i in range(40)], [f"P{i}" for i in range(12)])
    g = nx.Graph(); g.add_nodes_from(a.var_names)
    g.add_edges_from([("P0", "P1"), ("P1", "P2"), ("P3", "P11")], weight=1.0)
    g.graph["provenance"] = {"source": "toy", "version": "0", "url": "-", "sha256": "-"}
    return a, g


def test_unregistered_mode_raises_clearly(toy):
    if registered:
        pytest.skip("registered")
    with pytest.raises(NotImplementedError):
        select_features(*toy, 3, mode="hard_filter")


@impl
def test_filter_then_rank(toy):
    a, g = toy
    panel = select_features(a, g, 3, mode="hard_filter")
    in_graph = [n for n in a.var_names if g.degree(n) > 0 and candidates(a)[list(a.var_names).index(n)]]
    s = dict(zip(a.var_names, hvp_scores(a)))
    assert panel == sorted(in_graph, key=lambda n: -s[n])[:3]


@impl
def test_fills_from_outside_filter_when_short(toy):
    a, g = toy
    panel = select_features(a, g, 6, mode="hard_filter")
    assert len(panel) == len(set(panel)) == 6
    assert "P11" not in panel  # non-candidate never chosen
    assert set(panel[:4]) == {"P0", "P1", "P2", "P3"}


@impl
def test_deterministic(toy):
    a, g = toy
    assert select_features(a, g, 5, mode="hard_filter") == select_features(a, g, 5, mode="hard_filter")
