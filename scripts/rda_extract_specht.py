"""Extract the SCoPE2 (Specht et al. 2021) `peptides` assay + peptide->protein map from the scpdata
ExperimentHub object specht2019v3.Rda, without R (`pip install rdata`, build-time only).

    python scripts/rda_extract_specht.py <specht2019v3.Rda> <out.npz>

The scpdata `proteins` assay is already imputed (0% missing), so it can't be used for imputation benchmarks;
scripts/build_specht2021.py aggregates the (unimputed) peptides to proteins instead.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import rdata  # noqa: E402
from rda_common import attrs, cls, deref, pairlist, strvec  # noqa: E402

p = rdata.parser.parse_file(sys.argv[1], extension="rda")
qf = deref(pairlist(p.object)[0][1])
ld = attrs(attrs(qf)["ExperimentList"])["listData"]
names = strvec(attrs(ld)["names"])
sce = deref(deref(ld).value[names.index("peptides")])
A = attrs(sce)
lst = deref(attrs(deref(attrs(deref(A["assays"]))["data"]))["listData"])
m = deref(deref(lst).value[0])
ma = attrs(m)
dim = list(deref(ma["dim"]).value)
X = np.asarray(m.value, dtype=float).reshape(dim[1], dim[0]).T
dn = deref(ma["dimnames"])
rows, cols = strvec(dn.value[0]), strvec(dn.value[1])
em = deref(attrs(deref(A["rowRanges"]))["elementMetadata"])
rl = deref(attrs(em)["listData"])
rn = strvec(attrs(rl)["names"])
protein = strvec(deref(rl).value[rn.index("protein")])
cd = deref(attrs(qf)["colData"])
cda = attrs(cd)
cl = deref(cda["listData"])
cln = strvec(attrs(cl)["names"])
sm = deref(attrs(deref(attrs(qf)["sampleMap"]))["listData"])
smn = strvec(attrs(sm)["names"])
sm_assay_f = deref(sm).value[smn.index("assay")]
levels = strvec(attrs(sm_assay_f)["levels"])
sm_assay = [levels[i - 1] for i in deref(sm_assay_f).value]
sm_primary = strvec(deref(sm).value[smn.index("primary")])
sm_col = strvec(deref(sm).value[smn.index("colname")])
col2cell = {c: pr for a_, pr, c in zip(sm_assay, sm_primary, sm_col) if a_ == "peptides"}
# the matrix dimnames are internal ("i4"...); the SCE's own colData rownames carry the sample ids
sce_cols = strvec(attrs(deref(A["colData"]))["rownames"])
assert len(sce_cols) == X.shape[1], (len(sce_cols), X.shape)
col_cells = np.array([col2cell.get(c, c) for c in sce_cols])
np.savez_compressed(sys.argv[2], X=X, col_cells=col_cells, rows=np.array(rows), cols=np.array(cols), protein=np.array(protein),
                    cell_ids=np.array(strvec(cda["rownames"])),
                    sample_type=np.array(strvec(deref(cl).value[cln.index("SampleType")])))
print("peptides", X.shape, "NaN", round(float(np.isnan(X).mean()), 3), "proteins", len(set(protein)))
