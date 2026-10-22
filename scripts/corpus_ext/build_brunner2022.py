"""Corpus dataset brunner2022 -> data/cache/corpus/brunner2022.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub brunner2022.Rda (Homo sapiens HeLa, cell-cycle-arrested; Brunner et al. 2022
Mol Syst Biol; timsTOF label-free DIA, DIA-NN). Assay: `proteins` (the DIA-NN pg_matrix, MaxLFQ protein
quantities; DIA-NN does not impute). Missingness convention: NaN = missing (48% NaN, no zeros) -> real
missingness, protein assay used directly. The 247 MB object is too large for `rdata`; the assay was extracted
with scripts/corpus_ext/rda_stream_extract.py (same .npz layout as scripts/rda_extract_assay.py, plus rd_* rowData).
Single cells: all 434 runs are single HeLa cells (colData CellNumber == "1", SampleAnnotation 1cell/1Cell;
the dataset has no carrier/blank/bulk runs); the filter CellNumber == "1" is applied anyway.
Rows: rowData Protein.Group (accessions, ";"-separated) -> group_accessions -> first canonical accession.
Scale: raw MaxLFQ intensities -> log2 of positive values. Then the build_corpus.save() logic.

    python scripts/corpus_ext/build_brunner2022.py <proteins.npz>
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


d = np.load(sys.argv[1])
ncell = dict(zip(d["cd_rownames"], d["cd_CellNumber"]))
sc = np.array([ncell.get(c, "") == "1" for c in d["col_primary"]])
print("single cells:", int(sc.sum()), "of", sc.size)
X = log2_pos(d["X"][:, sc].T)
save("brunner2022", X, [(group_accessions(str(p)) or [""])[0] for p in d["rd_Protein.Group"]])
