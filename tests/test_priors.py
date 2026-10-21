"""Phase 1 priors: toy AnnData built from the snapshots (expected values derived in-test)."""

import networkx as nx
import numpy as np
import pytest

from scp_graphfs_mcp.complexes import load_complexes
from scp_graphfs_mcp.datasets import from_log2_matrix
from scp_graphfs_mcp.ids import uniprot_for_symbol
from scp_graphfs_mcp.priors import build_complex_graph, build_prior, build_string_graph, nulls, shuffled_null
from scp_graphfs_mcp.registry import validate_prior


def _proteasome_26s(source):
    df = load_complexes((source,))
    rows = df[df["name"].str.contains("26S proteasome", case=False)]
    assert not rows.empty, f"no 26S proteasome complex in {source} snapshot"
    return sorted(max(rows["members"], key=len))


@pytest.fixture(scope="module")
def toy():
    subunits = _proteasome_26s("corum")[:12]
    lonely = uniprot_for_symbol("MYH7")  # verified to be in no complex by test_variant_bridge
    ids = subunits[:-1] + [f"{subunits[-1]};Q00000"] + lonely  # include a protein-group id
    rng = np.random.default_rng(0)
    X = rng.normal(10, 1, (6, len(ids)))
    X[0, 0] = np.nan
    return from_log2_matrix(X, [f"c{i}" for i in range(6)], ids), ids, lonely[0]


@pytest.mark.parametrize("source", ["corum", "complexportal"])
def test_26s_proteasome_subunits_connected(toy, source):
    adata, ids, lonely = toy
    g = build_complex_graph(list(adata.var_names), source)
    in_complex = [i for i in ids if i != lonely]
    present = set(_proteasome_26s(source))
    in_complex = [i for i in in_complex if i.split(";")[0] in present]
    assert len(in_complex) >= 2
    assert nx.is_connected(g.subgraph(in_complex))
    assert g.degree(lonely) == 0
    validate_prior(g, ids)
    assert g.graph["coverage"]["unmapped_fraction"] == 0.0


def test_weight_counts_shared_complexes(toy):
    adata, ids, _ = toy
    g = build_complex_graph(ids, "corum")
    df = load_complexes(("corum",))
    u, v = ids[0], ids[1]
    expected = sum(1 for m in df["members"] if u in m and v in m)
    assert g.edges[u, v]["weight"] == expected


def test_null_preserves_degrees_and_is_seeded(toy):
    _, ids, _ = toy
    g = build_string_graph(ids, 400, "combined")
    h1, h2, h3 = shuffled_null(g, 1), shuffled_null(g, 1), shuffled_null(g, 2)
    assert dict(g.degree) == dict(h1.degree)
    assert set(h1.edges) == set(h2.edges)
    assert sorted(w for *_, w in g.edges(data="weight")) == sorted(w for *_, w in h1.edges(data="weight"))
    assert h1.graph["provenance"]["null_seed"] == 1 and h3.graph["provenance"]["null_seed"] == 2
    assert len(nulls(g, 3)) == 3


def test_all_registered_core_priors_build(toy):
    _, ids, _ = toy
    for name in ["corum", "complexportal", "string", "string_exp"]:
        validate_prior(build_prior(name, ids), ids)


def test_bad_string_args():
    with pytest.raises(ValueError):
        build_string_graph(["P28074"], 100)
    with pytest.raises(ValueError):
        build_string_graph(["P28074"], 700, "coexpression")
