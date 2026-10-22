"""Low-memory variant of scripts/rda_extract_assay.py (same .npz layout) built on rda_stream.py.

    python scripts/corpus_ext/rda_stream_extract.py <file.rda> <assay> <out.npz> [max_str]

Saves X (features x samples, as stored), rows, cols, col_primary, cd_rownames, cd_<colData col> (as strings)
and rd_<rowData col> for string/factor rowData columns.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rda_stream import dataframe, load_rda, qf_assays, sce_matrix  # noqa: E402

path, assay, out = sys.argv[1], sys.argv[2], sys.argv[3]
max_str = int(sys.argv[4]) if len(sys.argv) > 4 else 300_000
qf = load_rda(path, max_str=max_str)[0][1]
sce = qf_assays(qf)[assay]
m, dim = sce_matrix(sce)
X = np.asarray(m.value, dtype=float).reshape(dim[1], dim[0]).T
names = sce.attr.get("NAMES")
if names is not None and names.type == 16 and names.value is not None:
    rows = names.value
elif m.attr.get("dimnames") is not None and m.attr["dimnames"].value[0] is not None:
    rows = m.attr["dimnames"].value[0].value
else:  # RangedSummarizedExperiment: names live in rowRanges@partitioning@NAMES
    rows = sce.attr["rowRanges"].attr["partitioning"].attr["NAMES"].value
cols = sce.attr["colData"].attr["rownames"].value
extra = {}
cd_rn, cd = dataframe(qf.attr["colData"])
for k, v in cd.items():
    if v is not None:
        extra[f"cd_{k}"] = np.array(["" if x is None else str(x) for x in v])
rd_rn, rd = dataframe(sce.attr["elementMetadata"]) if "elementMetadata" in sce.attr else (None, {})
if not rd and "rowRanges" in sce.attr and "elementMetadata" in sce.attr["rowRanges"].attr:
    rd_rn, rd = dataframe(sce.attr["rowRanges"].attr["elementMetadata"])
for k, v in rd.items():
    if isinstance(v, list) and len(v) == len(rows):
        extra[f"rd_{k}"] = np.array(["" if x is None else str(x) for x in v])
_, sm = dataframe(qf.attr["sampleMap"])
keep = np.array(sm["assay"]) == assay
col2primary = dict(zip(np.array(sm["colname"])[keep], np.array(sm["primary"])[keep]))
col_primary = np.array([col2primary.get(c, "") for c in cols])
np.savez_compressed(out, X=X, col_primary=col_primary, rows=np.array(rows), cols=np.array(cols),
                    cd_rownames=np.array(cd_rn), **extra)
print(assay, X.shape, "NaN", round(float(np.isnan(X).mean()), 3), "zeros", round(float((X == 0).mean()), 3),
      "range", np.nanmin(X), np.nanmax(X), "rowData str cols", [k for k in extra if k.startswith("rd_")])
