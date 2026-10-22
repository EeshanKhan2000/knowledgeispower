"""Dump the rowData (string columns) of one QFeatures assay from a scpdata .Rda to .npz, without R.

    python scripts/corpus_ext/rda_extract_rowdata.py <file.Rda> <assay> <out.npz>

Complements scripts/rda_extract_assay.py for assays whose row names are bare indices ("1", "2", ...) and
whose protein IDs live in rowData. SingleCellExperiment keeps rowData either in `elementMetadata` or in
`rowRanges@elementMetadata`; both are checked. Saves `rows` (row names, same order as the assay matrix that
rda_extract_assay.py writes) and `rd_<column>` for every string rowData column. Uses `rdata` (small files).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import rdata  # noqa: E402
from rda_common import attrs, deref, pairlist, strvec  # noqa: E402

p = rdata.parser.parse_file(sys.argv[1], extension="rda")
qf = deref(pairlist(p.object)[0][1])
ld = attrs(attrs(qf)["ExperimentList"])["listData"]
names = strvec(attrs(ld)["names"])
sce = deref(ld).value[names.index(sys.argv[2])]
A = attrs(sce)
lst = deref(attrs(deref(attrs(deref(A["assays"]))["data"]))["listData"])
ma = attrs(deref(deref(lst).value[0]))
rows = strvec(A["NAMES"]) if "NAMES" in A and deref(A["NAMES"]).info.type.name == "STR" else strvec(deref(ma["dimnames"]).value[0])
extra = {}
for holder in (A, attrs(A["rowRanges"]) if "rowRanges" in A else {}):
    if "elementMetadata" not in holder:
        continue
    em = attrs(holder["elementMetadata"])
    if "listData" not in em or deref(em["listData"]).value is None:
        continue
    cl = deref(em["listData"])
    for n, v in zip(strvec(attrs(cl)["names"]), cl.value):
        v = deref(v)
        if v.info.type.name == "STR" and len(v.value) == len(rows) and f"rd_{n}" not in extra:
            extra[f"rd_{n}"] = np.array(["" if x is None else x for x in strvec(v)])
np.savez_compressed(sys.argv[3], rows=np.array(rows), **extra)
print(sys.argv[2], len(rows), "rows; rowData str cols:", len(extra), sorted(extra)[:12])
