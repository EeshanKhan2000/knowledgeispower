"""Corpus dataset hu2023_K562 -> data/cache/corpus/hu2023_K562.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub hu2023_K562.Rda (Homo sapiens K562; Hu et al. 2023 J Phys Chem B; label-free,
Proteome Discoverer 2.4 with MBR). The object is a bare SingleCellExperiment (not a QFeatures), so
scripts/rda_extract_assay.py does not apply; this script reads the .Rda directly with `rdata` (small file).
Assay: the single protein assay (`proteins_K562` in the scpdata docs; the authors' `Norm` matrix,
1249 proteins x 69 samples, rows = single UniProt accessions). scpdata documents it as "69 single-cells with
zero imputation", i.e. missing values were filled with 0 -> 0 is treated as missing (4.5% zeros, no NaN).
Single cells: colData SampleType is "K562" for all 69 columns and the scpdata docs describe all 69 as single
cells, so none are removed. Scale: values are positive intensities (median ~1.2e4) -> log2 of positive values.
Then the build_corpus.save() logic.

    python scripts/corpus_ext/build_hu2023_K562.py data/cache/corpus_raw/hu2023_K562/hu2023_K562.Rda
"""
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import rdata  # noqa: E402
from rda_common import attrs, deref, pairlist, strvec  # noqa: E402

from scp_graphfs_mcp.ids import group_accessions  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "cache" / "corpus"


def save(name, X, accs):  # identical to scripts/build_corpus.py save()
    OUT.mkdir(parents=True, exist_ok=True)
    X = np.asarray(X, float)
    keep_cols = [i for i, a in enumerate(accs) if a]
    X, accs = X[:, keep_cols], [accs[i] for i in keep_cols]
    order = np.argsort(-(~np.isnan(X)).sum(0))
    seen, cols = set(), []
    for i in order:
        if accs[i] not in seen:
            seen.add(accs[i]); cols.append(i)
    cols.sort()
    X, accs = X[:, cols], [accs[i] for i in cols]
    X = X[(~np.isnan(X)).sum(1) >= 50]
    X = X - np.nanmedian(X, axis=1, keepdims=True)
    np.savez_compressed(OUT / f"{name}.npz", X=X.astype(np.float32), accs=np.array(accs))
    print(f"{name}: {X.shape[0]} cells x {X.shape[1]} proteins, missing {np.isnan(X).mean():.3f}, "
          f"p1/p50/p99 {np.round(np.nanpercentile(X, [1, 50, 99]), 3).tolist()}")


def assay_list(sce):
    return deref(attrs(deref(attrs(deref(attrs(sce)["assays"]))["data"]))["listData"])


p = rdata.parser.parse_file(sys.argv[1], extension="rda")
sce = deref(pairlist(p.object)[0][1])
m = deref(assay_list(sce).value[0])
if "dim" not in attrs(m):  # the stored assay slot wraps a second SingleCellExperiment holding the matrix
    m = deref(assay_list(m).value[0])
ma = attrs(m)
dim = [int(x) for x in deref(ma["dim"]).value]
M = np.asarray(m.value, dtype=float).reshape(dim[1], dim[0]).T  # proteins x samples
rows, cols = (strvec(x) for x in deref(ma["dimnames"]).value)
cd = attrs(deref(attrs(sce)["colData"]))
cl = deref(cd["listData"])
stype = dict(zip(strvec(cd["rownames"]), strvec(cl.value[strvec(attrs(cl)["names"]).index("SampleType")])))
keep = np.array([stype.get(c) == "K562" for c in cols])
X = M[:, keep].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
save("hu2023_K562", X, [(group_accessions(str(r)) or [""])[0] for r in rows])
