"""Corpus dataset woo2022_lung -> data/cache/corpus/woo2022_lung.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub woo2022_lung.Rda (Homo sapiens, primary human lung cells, nanoPOTS LFQ).
Assay: `proteins_LFQ` (MaxQuant LFQ intensities). Unimputed: 0 = not detected (69.7% zeros, no NaN), the same
convention as woo2022_macrophage, so 0 -> NaN.
Single cells: all 26 samples are single cells (every FileName contains `_SC_`; Resting / Non_Resting), so none
are removed. Scale: raw intensities -> log2 of positive values. Row IDs are MaxQuant protein groups
(`A;B`) -> first canonical UniProt accession via ids.group_accessions. Then the build_corpus.save() logic.

    python scripts/rda_extract_assay.py data/cache/corpus_raw/woo2022_lung/woo2022_lung.Rda proteins_LFQ \
        data/cache/corpus_raw/woo2022_lung/woo2022_lung_proteins_LFQ.npz
    python scripts/corpus_ext/build_woo2022_lung.py data/cache/corpus_raw/woo2022_lung/woo2022_lung_proteins_LFQ.npz
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
sc = np.array(["_SC_" in str(f) for f in d["cd_FileName"]])
st = dict(zip(d["cd_rownames"], sc))
keep = np.array([st.get(c, False) for c in d["col_primary"]])
X = d["X"][:, keep].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
save("woo2022_lung", X, [(group_accessions(str(r)) or [""])[0] for r in d["rows"]])
