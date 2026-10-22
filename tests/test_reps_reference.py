"""Bulk reference-panel / mechanistic representations (reps.ccle, reps.proteomehd, reps.pathwaycommons).

Skipped unless the raw downloads (scripts/fetch_features.sh, Amendment 9 ccle/proteomehd/indra section) are in
data/cache/reps/. Expected values are derived from the snapshots in-test.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from scp_graphfs_mcp.reps import ccle, pathwaycommons, proteomehd

PSMA1, PSMA2 = "P25786", "P25787"
VARS = [f"A0A024R1R8;{PSMA1}", PSMA2, "P25788", "P28066", "P04637", "Q00987", "P60709", "NOT_A_PROTEIN"]

needs_ccle = pytest.mark.skipif(not ccle.RAW.exists(), reason="CCLE download absent")
needs_phd = pytest.mark.skipif(not proteomehd.RAW_CSV.exists(), reason="ProteomeHD download absent")
needs_phd_coreg = pytest.mark.skipif(not proteomehd.RAW_COREG.exists(), reason="ProteomeHD scores absent")
needs_pc = pytest.mark.skipif(not pathwaycommons.RAW.exists(), reason="Pathway Commons download absent")


def _check_block(B, d):
    assert B.shape == (len(VARS), d + 1)
    has = B[:, -1]
    assert set(np.unique(has)) <= {0.0, 1.0}
    assert has[-1] == 0 and np.all(B[-1, :-1] == 0)          # unmapped -> has=0, zero features
    assert np.isfinite(B).all()


def _check_graph(g):
    assert isinstance(g, nx.Graph)
    assert set(g.nodes) == set(VARS)
    assert nx.number_of_selfloops(g) == 0
    assert all(w > 0 for _, _, w in g.edges(data="weight"))


@needs_ccle
def test_ccle():
    R, has = ccle.reference(VARS)
    X, index, lines, _ = ccle._panel()
    assert R.shape == (len(VARS), len(lines)) and has.dtype == bool
    assert has[0] and not has[-1] and np.isnan(R[-1]).all()
    obs = ~np.isnan(R[has])
    assert np.allclose(np.nanmean(R[has], 1), 0, atol=1e-6)
    a, b = R[0], R[1]
    m = ~np.isnan(a) & ~np.isnan(b)
    assert m.sum() >= 50 and np.corrcoef(a[m], b[m])[0, 1] > 0.5   # PSMA1 ~ PSMA2 across cell lines
    assert obs.any()
    g = ccle.corr_graph(VARS, top=3)
    _check_graph(g)
    assert g.has_edge(VARS[0], PSMA2)
    _check_block(ccle.block(VARS, d=8), 8)


@needs_phd
def test_proteomehd_reference_and_block():
    R, has = proteomehd.reference(VARS)
    X, _, _, _ = proteomehd._panel()
    assert R.shape == (len(VARS), X.shape[1]) and has[0] and not has[-1]
    _check_block(proteomehd.block(VARS, d=8), 8)
    g = proteomehd.corr_graph(VARS, top=3, method="pearson")
    _check_graph(g)


@needs_phd_coreg
def test_proteomehd_coregulation():
    S, rows, _ = proteomehd._coreg()
    g = proteomehd.corr_graph(VARS, top=3)
    _check_graph(g)
    assert g.has_edge(VARS[0], PSMA2)
    w = g[VARS[0]][PSMA2]["weight"]
    assert w > np.nanpercentile(S[:500, :500], 99)       # proteasome pair is among the top co-regulated


@needs_pc
def test_pathwaycommons():
    g = pathwaycommons.graph(VARS)
    _check_graph(g)
    assert g.has_edge("P04637", "Q00987")                 # TP53 - MDM2
    assert g.has_edge(VARS[0], PSMA2)
    B = pathwaycommons.block(VARS, d=3)
    assert B.shape[0] == len(VARS) and B[-1, -1] == 0
