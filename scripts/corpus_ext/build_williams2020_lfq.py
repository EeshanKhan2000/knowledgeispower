"""Corpus dataset williams2020_lfq -> data/cache/corpus/williams2020_lfq.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub williams2020_lfq.Rda (Homo sapiens MCF10A; Williams et al. 2020 Anal Chem;
label-free nanoPOTS, MaxQuant). Two LC gradients were searched separately and stored as separate assays.
Assays: `proteins_30min_intensity` and `proteins_60min_intensity` (MaxQuant protein-group "Intensity.*"
columns; raw summed intensities, not LFQ-normalised, not imputed). Missingness convention: 0 = missing (no NaN
in the assay; 45% / 56% zeros) -> real missingness, so the protein assays are used directly.
Single cells: colData NbCells == 1, which in this object is exactly the samples named "<grad>min_1_<k>"
(verified against colData NbCells: 11 at 30 min + 6 at 60 min). Blanks (0), 3/10/50-cell samples are removed.
The two gradients' single cells are stacked over the union of mapped accessions (a protein not quantified in
one search is NaN for those cells). Rows are MaxQuant Protein.IDs groups -> first canonical UniProt accession
(group_accessions; CON__/REV__ tokens never match). Scale: raw intensities -> log2 of positive values.
Then the build_corpus.save() logic.

    python scripts/corpus_ext/build_williams2020_lfq.py <proteins_30min_intensity.npz> <proteins_60min_intensity.npz>
    (.npz from scripts/rda_extract_assay.py on data/cache/corpus_raw/williams2020_lfq/williams2020_lfq.Rda)
"""
import re
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


parts = []
for path in sys.argv[1:3]:
    d = np.load(path)
    sc = np.array([bool(re.fullmatch(r"(30|60)min_1_\d+", c)) for c in d["col_primary"]])
    accs = [(group_accessions(str(r)) or [""])[0] for r in d["rows"]]
    parts.append((log2_pos(d["X"][:, sc].T), accs))
allacc = sorted({a for _, accs in parts for a in accs if a})
idx = {a: j for j, a in enumerate(allacc)}
blocks = []
for X, accs in parts:
    B = np.full((X.shape[0], len(allacc)), np.nan)
    # within one search, duplicate accessions: keep the most-detected row (same rule as save())
    det = (~np.isnan(X)).sum(0)
    for i in np.argsort(-det, kind="stable"):
        a = accs[i]
        if a and np.isnan(B[:, idx[a]]).all():
            B[:, idx[a]] = X[:, i]
    blocks.append(B)
save("williams2020_lfq", np.vstack(blocks), allacc)
