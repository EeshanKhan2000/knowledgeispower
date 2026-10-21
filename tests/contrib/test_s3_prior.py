"""S3 contract: a contributed prior is valid, provenance-logged, and gets an automatic null."""
import re

import pytest

from scp_graphfs_mcp.datasets import load_petrosius2023
from scp_graphfs_mcp.priors import build_prior, shuffled_null
from scp_graphfs_mcp.registry import PRIORS, load_contrib, validate_prior

load_contrib()
contrib_priors = [n for n, e in PRIORS.items() if e.contrib]


@pytest.mark.xfail(not contrib_priors, reason="S3 not registered yet", strict=True)
def test_contrib_prior_contract():
    assert contrib_priors
    ids = list(load_petrosius2023().var_names)
    prov = open("data/PROVENANCE.md").read()
    for name in contrib_priors:
        g = build_prior(name, ids)
        validate_prior(g, ids)
        sha = g.graph["provenance"]["sha256"]
        assert re.fullmatch(r"[0-9a-f]{64}", sha), "provenance sha256 must be a 64-hex SHA-256"
        assert sha in prov, "snapshot must be logged in data/PROVENANCE.md"
        assert g.number_of_edges() > 0
        h = shuffled_null(g, 0)
        assert dict(h.degree) == dict(g.degree)
