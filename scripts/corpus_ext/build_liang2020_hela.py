"""Corpus dataset liang2020_hela -> data/cache/corpus/liang2020_hela.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub liang2020_hela.Rda (Homo sapiens HeLa; Liang et al. 2020 Anal Chem; label-free,
MaxQuant). Assay: `proteins` (MaxQuant proteinGroups "Intensity.*" columns, raw, not imputed).
Missingness convention: 0 = missing (no NaN; 64% zeros overall) -> real missingness, protein assay used directly.
Single cells: samples HeLa_1cell_* (colData nbCells == 1: E12, E14, F8) -> only 3 cells; the 0-cell blanks and
10/150/500-cell samples are removed. Rows are bare indices, so protein IDs come from rowData `Protein` (scpdata's
protein row name, the first Majority.protein.IDs entry; extracted with scripts/corpus_ext/rda_extract_rowdata.py)
-> group_accessions -> first canonical accession. Scale: raw intensities -> log2 of positive values.
Then the build_corpus.save() logic.

    python scripts/corpus_ext/build_liang2020_hela.py <proteins.npz> <proteins_rowdata.npz>
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
    order = np.argsort(-(~np.isnan(X)).sum(0))  # collapse duplicate accessions (keep the most-detected column)
    seen, cols = set(), []
    for i in order:
        if accs[i] not in seen:
            seen.add(accs[i]); cols.append(i)
    cols.sort()
    X, accs = X[:, cols], [accs[i] for i in cols]
    X = X[(~np.isnan(X)).sum(1) >= 50]  # drop near-empty cells
    X = X - np.nanmedian(X, axis=1, keepdims=True)
    np.savez_compressed(OUT / f"{name}.npz", X=X.astype(np.float32), accs=np.array(accs))
    print(f"{name}: {X.shape[0]} cells x {X.shape[1]} proteins, missing {np.isnan(X).mean():.3f}, "
          f"p1/p50/p99 {np.round(np.nanpercentile(X, [1, 50, 99]), 3).tolist()}")


def log2_pos(X):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(X > 0, np.log2(X), np.nan)


d, r = np.load(sys.argv[1]), np.load(sys.argv[2])
assert (d["rows"] == r["rows"]).all()
sc = np.array(["_1cell_" in c for c in d["col_primary"]])
print("single cells:", list(d["col_primary"][sc]))
X = log2_pos(d["X"][:, sc].T)
save("liang2020_hela", X, [(group_accessions(str(p)) or [""])[0] for p in r["rd_Protein"]])
