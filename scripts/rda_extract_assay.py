"""Generic: dump one QFeatures assay (dense matrix) from a scpdata .Rda to .npz, without R.

    python scripts/rda_extract_assay.py <file.Rda> <assay> <out.npz>

Saves X (features x samples, as stored), rows, cols (the SCE colData row names) and the full QFeatures
colData as string columns (cd_<name>), so labels can be joined later. Needs `pip install rdata` (build only).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import rdata  # noqa: E402
from rda_common import attrs, deref, pairlist, strvec  # noqa: E402

p = rdata.parser.parse_file(sys.argv[1], extension="rda")
qf = deref(pairlist(p.object)[0][1])
ld = attrs(attrs(qf)["ExperimentList"])["listData"]
names = strvec(attrs(ld)["names"])
sce = deref(deref(ld).value[names.index(sys.argv[2])])
A = attrs(sce)
lst = deref(attrs(deref(attrs(deref(A["assays"]))["data"]))["listData"])
m = deref(deref(lst).value[0])
ma = attrs(m)
dim = [int(x) for x in deref(ma["dim"]).value]
X = np.asarray(m.value, dtype=float).reshape(dim[1], dim[0]).T
rows = strvec(A["NAMES"]) if "NAMES" in A and deref(A["NAMES"]).info.type.name == "STR" else strvec(deref(ma["dimnames"]).value[0])
cols = strvec(attrs(deref(A["colData"]))["rownames"])
cd = attrs(deref(attrs(qf)["colData"]))
cl = deref(cd["listData"])
cln = strvec(attrs(cl)["names"])
extra = {}
for n, v in zip(cln, deref(cl).value):
    v = deref(v)
    t = v.info.type.name
    if t == "STR":
        extra[f"cd_{n}"] = np.array(strvec(v))
    elif t == "INT" and "levels" in attrs(v):
        lv = strvec(attrs(v)["levels"])
        extra[f"cd_{n}"] = np.array([lv[i - 1] if i > 0 else "" for i in v.value])
sm = deref(attrs(deref(attrs(qf)["sampleMap"]))["listData"])
smn = strvec(attrs(sm)["names"])
f = deref(sm).value[smn.index("assay")]
lv = strvec(attrs(f)["levels"])
sm_assay = np.array([lv[i - 1] for i in deref(f).value])
sm_primary = np.array(strvec(deref(sm).value[smn.index("primary")]))
sm_col = np.array(strvec(deref(sm).value[smn.index("colname")]))
keep = sm_assay == sys.argv[2]
col2primary = dict(zip(sm_col[keep], sm_primary[keep]))
col_primary = np.array([col2primary.get(c, "") for c in cols])
np.savez_compressed(sys.argv[3], X=X, col_primary=col_primary, rows=np.array(rows), cols=np.array(cols),
                    cd_rownames=np.array(strvec(cd["rownames"])), **extra)
print(sys.argv[2], X.shape, "NaN", round(float(np.isnan(X).mean()), 3), "zeros", round(float((X == 0).mean()), 3),
      "range", np.nanmin(X), np.nanmax(X))
