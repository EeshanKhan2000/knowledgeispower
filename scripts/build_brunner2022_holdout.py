"""Build data/datasets/brunner2022_holdout.h5ad: the Amendment-13/14 holdout (HeLa, 5 cell-cycle groups, timsTOF DIA).

Input: data/cache/corpus_raw/brunner2022/proteins.npz (scpdata brunner2022.Rda `proteins` assay = DIA-NN MaxLFQ, NaN =
missing; extracted by scripts/corpus_ext/rda_stream_extract.py). Processing matches the corpus build (log2, protein IDs
from rowData Protein.Group, per-cell median-centring) but keeps cell labels in obs['cell_type'] = CellCycleStage.
Nothing is evaluated here: only shape and missingness are printed.

    python scripts/build_brunner2022_holdout.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from scp_graphfs_mcp.datasets import from_log2_matrix

ROOT = Path(__file__).resolve().parents[1]
d = np.load(ROOT / "data/cache/corpus_raw/brunner2022/proteins.npz", allow_pickle=False)
stage = dict(zip(d["cd_rownames"], d["cd_CellCycleStage"]))
ncell = dict(zip(d["cd_rownames"], d["cd_CellNumber"]))
cols = d["cols"]
keep = np.array([ncell.get(c) == "1" for c in cols])
X = d["X"].astype(float).T[keep]
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
X = X - np.nanmedian(X, axis=1, keepdims=True)
prot = d["rd_Protein.Group"].astype(str)
seen = ~np.isnan(X).all(0)
df = pd.DataFrame(X[:, seen], columns=prot[seen])
df = df.T.groupby(level=0).first().T  # protein groups are unique in a DIA-NN pg_matrix; guard anyway
cells = cols[keep]
a = from_log2_matrix(df.values, cells, df.columns.astype(str),
                     obs=pd.DataFrame({"cell_type": [stage[c] for c in cells]}, index=cells))
a.uns["dataset"] = {"name": "brunner2022_holdout", "source": "scpdata brunner2022.Rda `proteins` (DIA-NN MaxLFQ)",
                    "value": "log2, per-cell median-centred; NaN = missing",
                    "role": "HOLDOUT (Amendments 13-14): confirmation only"}
out = ROOT / "data" / "datasets" / "brunner2022_holdout.h5ad"
a.write_h5ad(out, compression="gzip")
print(a.shape, f"missing={np.isnan(np.asarray(a.X)).mean():.3f}", a.obs.cell_type.value_counts().to_dict())
