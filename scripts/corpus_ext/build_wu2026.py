"""Corpus dataset wu2026 -> data/cache/corpus/wu2026.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub EH10517 `wu2026.rda` (hosted at https://zenodo.org/records/22283331/files/wu2026.rda;
Species Homo sapiens; prenatal human brain, gestational weeks 13/15/19, label-free DIA-NN, PRIDE PXD071075;
all protein-group entries are `*_HUMAN`).
Assay: `imported_proteins` (DIA-NN protein-group matrix, 4401 groups x 2310 runs), raw intensities, unimputed
(90.6% NaN, no zeros). Chosen over the scpdata `proteins` assay (5107 x 2310, log scale) because that one has
97.2% NaN plus 619 -Inf entries (log of 0) and fewer proteins per cell; `imported_proteins` is the
untransformed protein-level quantification with genuine missingness.
Scale: raw intensities -> log2 of positive values (non-positive -> NaN).
Single cells: every run is one cell (colData `dataset` = S1/S2/S3 x germinal zone GZ / cortical plate CP; no
carrier, blank, reference or bulk samples are listed), so all 2310 runs are kept before the >=50-protein filter.
Row IDs are DIA-NN protein groups -> first canonical accession (ids.group_accessions). Then the
build_corpus.py save() logic. < 10,000 cells, so no subsampling.

The .rda is too large for `rdata` in 15 GB RAM, so the assay is extracted with the low-memory reader:
    python scripts/corpus_ext/rda_stream_extract.py data/cache/corpus_raw/wu2026/wu2026.rda imported_proteins \
        data/cache/corpus_raw/wu2026/imported_proteins.npz
    python scripts/corpus_ext/build_wu2026.py data/cache/corpus_raw/wu2026/imported_proteins.npz
"""
import sys
from pathlib import Path

import numpy as np

from scp_graphfs_mcp.ids import group_accessions

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


d = np.load(sys.argv[1])
ds = dict(zip(d["cd_rownames"], d["cd_dataset"]))
keep = np.array([ds.get(c, "") in ("S1_GZ", "S1_CP", "S2_GZ", "S2_CP", "S3_GZ") for c in d["col_primary"]])
print("runs kept", int(keep.sum()), "of", keep.size)
X = d["X"][:, keep].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
save("wu2026", X, [(group_accessions(str(r)) or [""])[0] for r in d["rows"]])
