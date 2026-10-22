"""Shape / has-column / sanity checks for the ProtT5, PDB co-structure and Pharos representations.

Skipped when the raw caches (scripts/fetch_features.sh, Amendment 9 section) are absent.
"""

import numpy as np
import pytest

pytest.importorskip("h5py")

from scp_graphfs_mcp.reps import pdb_costructure, pharos, prott5  # noqa: E402

# PSMA1, PSMA2 (20S proteasome alpha subunits), a two-accession group, and a non-accession.
VAR = ["P25786", "P25787", "P25786-2;Q9Y2S6", "NOT_AN_ACCESSION"]


def _need(path):
    if not path.exists():
        pytest.skip(f"raw cache missing: {path}")


def _check_block(B, d):
    assert B.shape == (len(VAR), d + 1)
    assert np.isfinite(B).all()
    assert set(np.unique(B[:, -1])) <= {0.0, 1.0}
    assert B[-1, -1] == 0.0 and not B[-1, :-1].any()  # missing protein -> all-zero row, has=0


def test_prott5():
    _need(prott5.RAW_PATH)
    B = prott5.block(VAR, d=8)
    _check_block(B, 8)
    assert B[:3, -1].tolist() == [1.0, 1.0, 1.0]
    E, has = prott5.embedding(VAR)
    assert E.shape == (len(VAR), 1024) and has.tolist() == [True, True, True, False]


def test_pdb_costructure():
    _need(pdb_costructure.RAW_PATH)
    g = pdb_costructure.graph(VAR)
    assert set(g.nodes) == set(VAR)
    assert g.has_edge("P25786", "P25787") and g["P25786"]["P25787"]["weight"] >= 1
    # the isoform group maps to P25786 too, so it is linked to PSMA2 but not to itself
    assert g.has_edge("P25786-2;Q9Y2S6", "P25787")
    assert all(u != v for u, v in g.edges)
    assert g.degree("NOT_AN_ACCESSION") == 0


def test_pharos():
    _need(pharos.RAW_PATH)
    B = pharos.block(VAR)
    t = pharos.table()
    n_fam = sum(1 for f in t["fam"].unique() if f)
    _check_block(B, len(pharos.TDLS) + n_fam + 4)
    assert B[:3, -1].tolist() == [1.0, 1.0, 1.0]
    assert t.loc["P25786", "tdl"] in pharos.TDLS
