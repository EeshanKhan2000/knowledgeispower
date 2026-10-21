"""Build data/datasets/leduc2022_pscope_proteins_norm2.h5ad from the scpdata ExperimentHub object.

Source: https://mghp.osn.xsede.org/bir190004-bucket01/ExperimentHub/scpdata/leduc2022_pSCoPE.Rda
(SHA-256 in data/PROVENANCE.md). R is not required: scripts/rda_extract_leduc.py (pure Python,
`rdata` package, build-time only) dumps the QFeatures assay `proteins_norm2` - the protein-level
matrix BEFORE imputation - to an .npz, which this script turns into AnnData.

    python scripts/rda_extract_leduc.py <Rda> <out.npz>       # needs `pip install rdata` (build only)
    python scripts/build_leduc2022.py <out.npz>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scp_graphfs_mcp.datasets import from_log2_matrix

ROOT = Path(__file__).resolve().parents[1]
d = np.load(sys.argv[1], allow_pickle=False)
X = d["X"].T  # cells x proteins
cells, proteins = d["cols"], d["rows"]
st = dict(zip(d["cell_ids"], d["sample_type"]))
ctype = np.array([st.get(c, "NA") for c in cells])
keep = np.isin(ctype, ["Melanoma", "Monocyte"]) & ~np.all(np.isnan(X), axis=1)
X, cells, ctype = X[keep], cells[keep], ctype[keep]
pkeep = ~np.all(np.isnan(X), axis=0)
X, proteins = X[:, pkeep], proteins[pkeep]
a = from_log2_matrix(X, cells, proteins, obs=pd.DataFrame({"cell_type": ctype}, index=cells))
a.uns["dataset"] = {
    "name": "leduc2022_pscope_proteins_norm2",
    "source": "scpdata ExperimentHub leduc2022_pSCoPE.Rda, QFeatures assay 'proteins_norm2' (pre-imputation)",
    "citation": "Leduc A, Huffman RG, Cantlon J, Khan S, Slavov N. Genome Biology 23, 261 (2022). doi:10.1186/s13059-022-02817-5",
    "value": "log2 relative protein quantity (normalised, centred); NaN = missing",
    "note": "layers['raw'] = 2**X of relative values (convention only; not absolute intensities)",
}
out = ROOT / "data" / "datasets" / "leduc2022_pscope_proteins_norm2.h5ad"
a.write_h5ad(out, compression="gzip")
print(a, f"missing={np.isnan(np.asarray(a.X)).mean():.3f}", a.obs.cell_type.value_counts().to_dict(), out)
