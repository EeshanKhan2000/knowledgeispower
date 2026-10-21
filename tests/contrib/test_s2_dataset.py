"""S2 contract: a contributed dataset with real (unimputed) missingness."""
import re

import numpy as np
import pytest

from scp_graphfs_mcp.registry import DATASETS, load_contrib, validate_dataset

load_contrib()
contrib_ds = [n for n, e in DATASETS.items() if e.contrib]


@pytest.mark.xfail(not contrib_ds, reason="S2 not registered yet", strict=True)
def test_contrib_dataset_contract():
    assert contrib_ds
    for name in contrib_ds:
        a = DATASETS[name].load()
        validate_dataset(a)
        assert a.n_vars >= 500
        assert np.isnan(np.asarray(a.X, float)).mean() >= 0.2, "must be unimputed"
        assert "cell_type" in a.obs
        prov = open("data/PROVENANCE.md").read()
        sha = a.uns.get("source_sha256", "")
        assert re.fullmatch(r"[0-9a-f]{64}", sha), "set adata.uns['source_sha256'] to the source file's SHA-256"
        assert sha in prov, "source SHA-256 must have a row in data/PROVENANCE.md"
