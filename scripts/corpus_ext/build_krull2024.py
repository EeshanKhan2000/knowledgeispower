"""Corpus dataset krull2024 -> data/cache/corpus/krull2024.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub krull2024.Rda (Homo sapiens U-2 OS, control vs IFN-gamma; DIA-NN 1.8 DIA-ME,
timsTOF Pro). Assay: `proteins` (DIA-NN protein-group matrix, 1553 x 143). Unimputed: 0 = not quantified
(63.0% zeros, no NaN) -> NaN. Row names are bare indices, so protein IDs come from rowData `Protein.Group`
(saved as rd_Protein.Group by scripts/corpus_ext/rda_stream_extract.py) -> first canonical UniProt accession.
Single cells: colData `SampleAnnotation` is "SC" (143) or "10SC" (15 ten-cell enhancer runs); only "SC" columns
are kept (the protein assay already holds exactly the 143 SC runs). Scale: positive intensities -> log2.
Then the build_corpus.save() logic.

    python scripts/corpus_ext/rda_stream_extract.py data/cache/corpus_raw/krull2024/krull2024.Rda proteins \
        data/cache/corpus_raw/krull2024/krull2024_proteins.npz
    python scripts/corpus_ext/build_krull2024.py data/cache/corpus_raw/krull2024/krull2024_proteins.npz
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
sa = dict(zip(d["cd_rownames"], d["cd_SampleAnnotation"]))
keep = np.array([sa.get(c, "") == "SC" for c in d["col_primary"]])
X = d["X"][:, keep].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
save("krull2024", X, [(group_accessions(str(r)) or [""])[0] for r in d["rd_Protein.Group"]])
