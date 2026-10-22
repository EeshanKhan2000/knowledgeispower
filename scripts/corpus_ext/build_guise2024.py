"""Corpus dataset guise2024 -> data/cache/corpus/guise2024.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub guise2024.rda (Homo sapiens; LCM-isolated postmortem spinal motor neurons,
ALS / control donors; nanoPOTS label-free, Proteome Discoverer 2.5). Assay: `proteins` (PD protein abundances,
4437 x 108; row names = master UniProt accessions). Unimputed: 51.1% NaN, no zeros -> NaN = missing.
Single cells: every sample is one LCM-captured motor neuron, but scpdata could not find annotations for 8 runs
(F5, F8, F21, F34, F42, F61, F77, F88; Diagnosis/DonorID = "None"); since their sample type cannot be checked
they are excluded, leaving the 100 annotated neurons (Diagnosis ALS or CTL). Scale: positive intensities -> log2.
Then the build_corpus.save() logic.

    python scripts/corpus_ext/rda_stream_extract.py data/cache/corpus_raw/guise2024/guise2024.rda proteins \
        data/cache/corpus_raw/guise2024/guise2024_proteins.npz
    python scripts/corpus_ext/build_guise2024.py data/cache/corpus_raw/guise2024/guise2024_proteins.npz
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
dx = dict(zip(d["cd_rownames"], d["cd_Diagnosis"]))
keep = np.array([dx.get(c, "") in ("ALS", "CTL") for c in d["col_primary"]])
X = d["X"][:, keep].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
save("guise2024", X, [(group_accessions(str(r)) or [""])[0] for r in d["rows"]])
