"""Build data/datasets/khan2023_proteins_unimputed.h5ad: the reserved holdout (EXPLORATION.md Amendments 4 and 9).

Input: the .npz from `scripts/rda_extract_assay.py khan2023.Rda proteins_unimputed <out.npz>` (scpdata khan2023.Rda;
MCF-10A cells at days 0/3/9 of TGF-beta-induced EMT; SCoPE2/pSCoPE TMTPro 16plex). The `proteins_unimputed` assay is
already log2 relative abundance (median ~0). Only single cells (Day_0/3/9) are kept; proteins never observed are dropped.
Nothing is evaluated here: this script only checks shape and missingness.

    python scripts/build_khan2023.py <khan2023_proteins_unimputed.npz>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scp_graphfs_mcp.datasets import from_log2_matrix

ROOT = Path(__file__).resolve().parents[1]
d = np.load(sys.argv[1], allow_pickle=False)
st = dict(zip(d["cd_rownames"], d["cd_SampleType"]))
ctype = np.array([st.get(c, "NA") for c in d["cols"]])
keep = np.isin(ctype, ["Day_0", "Day_3", "Day_9"])
X = d["X"].astype(float).T[keep]
seen = ~np.isnan(X).all(0)
cells = d["cols"][keep]
a = from_log2_matrix(X[:, seen], cells, d["rows"][seen].astype(str), obs=pd.DataFrame({"cell_type": ctype[keep]}, index=cells))
a.uns["dataset"] = {
    "name": "khan2023_proteins_unimputed",
    "source": "scpdata ExperimentHub khan2023.Rda, `proteins_unimputed` assay",
    "citation": "Khan S et al. 2023, MCF-10A EMT single-cell proteomics (see scpdata khan2023 metadata; MassIVE)",
    "value": "log2 relative quantity; NaN = missing",
    "role": "HOLDOUT: confirmation only (Amendment 9); never used for development",
}
out = ROOT / "data" / "datasets" / "khan2023_proteins_unimputed.h5ad"
a.write_h5ad(out, compression="gzip")
print(a.shape, f"missing={np.isnan(np.asarray(a.X)).mean():.3f}", a.obs.cell_type.value_counts().to_dict())
