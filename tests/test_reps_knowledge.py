"""Knowledge-source representation modules (scp_graphfs_mcp.reps: reactome, biogrid, intact, monarch,
cocitation). Skipped when the raw downloads in data/cache/reps/ are absent (scripts/fetch_features.sh)."""

from __future__ import annotations

import importlib

import networkx as nx
import numpy as np
import pytest

from scp_graphfs_mcp.reps._kbutil import source_dir

RAW = {
    "reactome": ["UniProt2Reactome_All_Levels.txt", "UniProt2Reactome.txt"],
    "biogrid": ["BIOGRID-ORGANISM-LATEST.tab3.zip"],
    "intact": ["intact-micluster.zip"],
    "monarch": ["gene_to_phenotypic_feature_association.all.tsv.gz",
                "causal_gene_to_disease_association.all.tsv.gz",
                "correlated_gene_to_disease_association.all.tsv.gz"],
    "cocitation": ["gene2pubmed.gz"],
}
BLOCK_D = {"reactome": 32, "biogrid": 16, "intact": 16, "monarch": 24, "cocitation": 16}
GRAPH = {"reactome", "biogrid", "intact", "cocitation"}

# PSMA1 / PSMA2 (20S proteasome alpha subunits), as protein groups; plus a non-protein id.
PSMA1, PSMA2 = "P25786", "P25787"
VAR = [f"{PSMA1}-2;A0A000XXX0", PSMA2, "P28074", "P60709", "P04637", "Q9Y2S6", "not_a_protein"]


def _mod(name):
    if not all((source_dir(name) / f).exists() for f in RAW[name]):
        pytest.skip(f"{name} raw files absent in {source_dir(name)}")
    return importlib.import_module(f"scp_graphfs_mcp.reps.{name}")


def _check_block(B, p, d):
    assert B.shape == (p, d + 1)
    assert np.isfinite(B).all()
    has = B[:, -1]
    assert set(np.unique(has)) <= {0.0, 1.0}
    assert (B[has == 0, :-1] == 0).all()
    return has.astype(bool)


@pytest.mark.parametrize("name", sorted(RAW))
def test_block_shape_and_has(name):
    mod = _mod(name)
    B = mod.block(VAR, d=BLOCK_D[name])
    # tiny var lists cannot support d SVD/spectral components; only the has column is guaranteed
    assert B.shape[0] == len(VAR) and B.shape[1] <= BLOCK_D[name] + 1
    has = B[:, -1].astype(bool)
    assert not has[-1]  # non-protein id never has data


@pytest.mark.parametrize("name", sorted(GRAPH))
def test_graph_convention(name):
    mod = _mod(name)
    g = mod.graph(VAR)
    assert isinstance(g, nx.Graph)
    assert set(g.nodes) == set(VAR)
    for u, v, w in g.edges(data="weight"):
        assert u != v and isinstance(w, float) and w > 0
    assert g.degree("not_a_protein") == 0


def test_biogrid_psma1_psma2_linked():
    g = _mod("biogrid").graph(VAR)
    assert g.has_edge(VAR[0], PSMA2)
    assert g[VAR[0]][PSMA2]["weight"] >= 1


def test_reactome_psma1_psma2_share_pathway():
    mod = _mod("reactome")
    sets = mod._sets()
    assert sets["all_levels"][PSMA1] & sets["all_levels"][PSMA2]
    shared_low = sets["lowest"][PSMA1] & sets["lowest"][PSMA2]
    g = mod.graph(VAR)
    # an edge exists iff they share a lowest-level pathway with <= MAX_PATHWAY members
    low_members: dict[str, int] = {}
    for pws in sets["lowest"].values():
        for pw in pws:
            low_members[pw] = low_members.get(pw, 0) + 1
    n_small = sum(1 for pw in shared_low if low_members[pw] <= mod.MAX_PATHWAY)
    assert g.has_edge(VAR[0], PSMA2) == (n_small > 0)
    if n_small:
        assert g[VAR[0]][PSMA2]["weight"] == n_small


def test_monarch_disease_block():
    mod = _mod("monarch")
    B = mod.disease_block(VAR, d=16)
    assert B.shape[0] == len(VAR) and not B[-1, -1]


@pytest.mark.parametrize("name", sorted(RAW))
def test_dataset_blocks(name):
    from scp_graphfs_mcp.datasets import load_petrosius2023

    mod = _mod(name)
    var = list(load_petrosius2023().var_names)
    has = _check_block(mod.block(var, d=BLOCK_D[name]), len(var), BLOCK_D[name])
    assert has.mean() > 0.05
    if name in GRAPH:
        g = mod.graph(var)
        assert g.number_of_nodes() == len(var) and g.number_of_edges() > 0
