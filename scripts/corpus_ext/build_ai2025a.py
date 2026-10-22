"""Corpus dataset ai2025a -> data/cache/corpus/ai2025a.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub EH9627 `ai2025a.rda` (Species Homo sapiens; adult human cardiomyocytes from
3 donors, timsTOF DIA-NN LFQ; all 2044 protein groups are `*_HUMAN` entries).
Assay: `proteins` (2044 protein groups x 299 runs). Unimputed: 65.0% NaN, no zeros.
Scale: already log2 (values 3.7-22.9, run assays are raw and the `precursors_log` assay is their log2), kept.
Single cells: every run is one cardiomyocyte from a heart region (HeartLocation Lvepi/Lvendo/Lvmid/RV, Subjects 3
and 4; 278 runs). The 21 runs labelled HeartLocation `sytox` (all of Subject5) are excluded: they are not one of
the region groups and their sample type is not documented in the metadata, so they are dropped conservatively.
No carrier/blank/bulk samples are listed. Row IDs are DIA-NN protein groups -> first canonical accession
(ids.group_accessions). Then the build_corpus.py save() logic.

The .rda is too large for `rdata` in 15 GB RAM, so the assay is extracted with the low-memory reader:
    python scripts/corpus_ext/rda_stream_extract.py data/cache/corpus_raw/ai2025a/ai2025a.rda proteins \
        data/cache/corpus_raw/ai2025a/proteins.npz
    python scripts/corpus_ext/build_ai2025a.py data/cache/corpus_raw/ai2025a/proteins.npz
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
loc = dict(zip(d["cd_rownames"], d["cd_HeartLocation"]))
keep = np.array([loc.get(c, "") in ("Lvepi", "Lvendo", "Lvmid", "RV") for c in d["col_primary"]])
print("runs kept", int(keep.sum()), "of", keep.size)
X = d["X"][:, keep].T  # already log2; NaN = missing
save("ai2025a", X, [(group_accessions(str(r)) or [""])[0] for r in d["rows"]])
