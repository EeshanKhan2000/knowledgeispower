"""Corpus dataset williams2020_tmt -> data/cache/corpus/williams2020_tmt.npz (cells x UniProt, log2, median-centred).

Source: scpdata ExperimentHub williams2020_tmt.Rda (Homo sapiens AML lines MOLM-14, K562, CMK; Williams et al.
2020 Anal Chem; nanoPOTS TMT-11, MaxQuant). Assay: `proteins_corrected` (MaxQuant protein-group
"Reporter intensity corrected" = isotope-impurity-corrected reporter ion intensities; not imputed).
Missingness convention: 0 = missing (no NaN; 33% zeros) -> real missingness, protein assay used directly.
Single cells: colData Amount == "1cell" (8 channels per batch: MOLM-14 / K562 / CMK); the 10 ng " Boost"
carrier, 0.2 ng "Reference" and "Empty" channels are removed (19 batches -> 152 cells before the 50-protein filter).
Rows are UniProt *entry names* (e.g. 1433B_HUMAN), not accessions; each group is mapped to the accession of its
first token that is a current Swiss-Prot human entry name, using the UniProt REST table
data/cache/corpus_raw/williams2020_tmt/uniprot_human_sp_entrynames.tsv
(https://rest.uniprot.org/uniprotkb/stream?query=organism_id:9606+AND+reviewed:true&fields=accession,id&format=tsv).
CON__/REV__ tokens are ignored; groups whose entry names were all renamed since 2020 (mostly HLA alleles) do not
map and are dropped (no guessing). Scale: raw reporter intensities -> log2 of positive values.
Then the build_corpus.save() logic.

    python scripts/corpus_ext/build_williams2020_tmt.py <proteins_corrected.npz> <uniprot_human_sp_entrynames.tsv>
    (.npz from scripts/rda_extract_assay.py on data/cache/corpus_raw/williams2020_tmt/williams2020_tmt.Rda)
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
name2acc = {}
with open(sys.argv[2]) as f:
    next(f)
    for line in f:
        acc, entry = line.rstrip("\n").split("\t")[:2]
        name2acc[entry] = acc
amount = dict(zip(d["cd_rownames"], d["cd_Amount"]))
sc = np.array([amount.get(c, "") == "1cell" for c in d["col_primary"]])
X = log2_pos(d["X"][:, sc].T)
accs = []
for r in d["rows"]:
    hits = [name2acc[t] for t in str(r).split(";") if not t.startswith(("CON__", "REV__")) and t in name2acc]
    accs.append(hits[0] if hits else "")
print(f"rows mapped {sum(map(bool, accs))}/{len(accs)}, single cells {int(sc.sum())}")
save("williams2020_tmt", X, accs)
