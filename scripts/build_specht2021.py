"""Build data/datasets/specht2021_scope2_proteins_from_peptides.h5ad (third, held-out dataset).

Input: the .npz from scripts/rda_extract_specht.py (scpdata specht2019v3.Rda, `peptides` assay, unimputed).
Proteins = median over that protein's peptides in each cell (missing peptides ignored; all-missing -> NaN).
That's the usual SCoPE2 aggregation, applied *before* any imputation.

    python scripts/build_specht2021.py <peptides.npz>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scp_graphfs_mcp.datasets import from_log2_matrix

ROOT = Path(__file__).resolve().parents[1]
d = np.load(sys.argv[1], allow_pickle=False)
pep = pd.DataFrame(d["X"].T, columns=d["rows"])  # cells x peptides
prot = pd.Series(d["protein"], index=d["rows"])
P = pep.T.groupby(prot.values).median().T  # cells x proteins (nan-aware median)
st = dict(zip(d["cell_ids"], d["sample_type"]))
ctype = np.array([st.get(c, "NA") for c in d["col_cells"]])
keep = np.isin(ctype, ["Macrophage", "Monocyte"])
P = P.loc[keep]
P = P.loc[:, P.notna().any(axis=0)]
cells = d["col_cells"][keep]
a = from_log2_matrix(P.values, cells, P.columns.astype(str),
                     obs=pd.DataFrame({"cell_type": ctype[keep]}, index=cells))
a.uns["dataset"] = {
    "name": "specht2021_scope2_proteins_from_peptides",
    "source": "scpdata ExperimentHub specht2019v3.Rda, `peptides` assay (unimputed), median-aggregated to proteins",
    "citation": "Specht H et al. Single-cell proteomic and transcriptomic analysis of macrophage heterogeneity using SCoPE2. Genome Biology 22, 50 (2021).",
    "value": "log2 relative quantity; NaN = missing",
}
out = ROOT / "data" / "datasets" / "specht2021_scope2_proteins_from_peptides.h5ad"
a.write_h5ad(out, compression="gzip")
print(a.shape, f"missing={np.isnan(np.asarray(a.X)).mean():.3f}", a.obs.cell_type.value_counts().to_dict())
