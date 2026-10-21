import sys, numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
import rdata
from rda_common import *
p = rdata.parser.parse_file(sys.argv[1], extension="rda")
qf = deref(pairlist(p.object)[0][1])
ld = attrs(attrs(qf)["ExperimentList"])["listData"]
names = strvec(attrs(ld)["names"])
sce = deref(deref(ld).value[names.index("proteins_norm2")])
A = attrs(sce)
assays = deref(A["assays"]); print("assays cls", cls(assays), list(attrs(assays)))
data = deref(attrs(assays)["data"]); print("data cls", cls(data), list(attrs(data)))
lst = deref(attrs(data)["listData"]); print("listData", lst.info.type.name, len(lst.value), list(attrs(lst)))
m = deref(deref(lst).value[0]); ma = attrs(m)
dim = list(deref(ma["dim"]).value); print("dim", dim, m.info.type.name)
X = np.asarray(m.value, dtype=float).reshape(dim[1], dim[0]).T  # R is column-major
dn = deref(ma["dimnames"]) if "dimnames" in ma else None
rows = strvec(dn.value[0]) if dn is not None and deref(dn.value[0]).info.type.name == "STR" else strvec(A["NAMES"])
cols = strvec(dn.value[1]) if dn is not None and deref(dn.value[1]).info.type.name == "STR" else None
print("rows", rows[:3], "cols", (cols or [])[:3])
cd = deref(attrs(qf)["colData"]); cda = attrs(cd)
cell_ids = strvec(cda["rownames"]); cl = deref(cda["listData"]); cln = strvec(attrs(cl)["names"])
st = strvec(deref(cl).value[cln.index("SampleType")])
np.savez_compressed(sys.argv[2], X=X, rows=np.array(rows), cols=np.array(cols), cell_ids=np.array(cell_ids), sample_type=np.array(st))
print("NaN frac", np.isnan(X).mean(), "range", np.nanmin(X), np.nanmax(X))
