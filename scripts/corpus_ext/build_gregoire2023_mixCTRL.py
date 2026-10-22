"""Corpus dataset gregoire2023_mixCTRL -> data/cache/corpus/gregoire2023_mixCTRL.npz (cells x UniProt, log2, centred).

Source: scpdata ExperimentHub gregoire2023_mixCTRL.Rda (Homo sapiens THP-1 / U-937 monocytes and PMA-
differentiated macrophage-like cells; SCoPE2 TMTpro-16, Sage). Protein data exist only per acquisition batch:
`proteins_<batch>_norm_log` (7 assays, scpdata assays 106-112: normalised, log2-transformed peptides aggregated
to proteins) and `proteins_<batch>_batchC` (113-119, additionally batch-corrected for run and channel). We use
the `_norm_log` assays: unimputed (24.9-44.3% NaN per batch; scpdata states the imputed assays were not
reproduced), and they correspond to leduc2022 `proteins_norm2` (normalised, pre-batch-correction, pre-imputation).
The 7 batches are stacked as rows (cells) and joined on the protein-group ID (union; absent = NaN).
Single cells: keep colData sample_type == "SC" and cell_number == 1. Excluded: "SCeq" samples (single-cell
equivalents, i.e. diluted lysate, including all "mix" samples) and 2- / 4-cell samples. Carrier, blank and unused
TMT channels are not part of the protein assays (PSM level only). Scale: already log2 (ratio scale, median ~0), kept.
Row IDs are Sage protein groups (`sp|ACC|NAME;...`) -> first canonical UniProt accession. Then build_corpus.save().

    # step 1 (one parse of the .Rda; writes the extracted assays):
    python scripts/corpus_ext/build_gregoire2023_mixCTRL.py extract data/cache/corpus_raw/gregoire2023_mixCTRL/gregoire2023_mixCTRL.Rda \
        data/cache/corpus_raw/gregoire2023_mixCTRL/gregoire2023_mixCTRL_proteins_norm_log.npz
    # step 2:
    python scripts/corpus_ext/build_gregoire2023_mixCTRL.py build data/cache/corpus_raw/gregoire2023_mixCTRL/gregoire2023_mixCTRL_proteins_norm_log.npz
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scp_graphfs_mcp.ids import group_accessions

BATCHES = ["CBIO680", "CBIO681", "CBIO703", "CBIO715", "CBIO725", "CBIO754", "GIGA"]

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


def extract(rda, out):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rda_stream import dataframe, load_rda, qf_assays, sce_matrix

    qf = load_rda(rda)[0][1]
    assays = qf_assays(qf)
    _, sm = dataframe(qf.attr["sampleMap"])
    cd_rn, cd = dataframe(qf.attr["colData"])
    res = {"cd_rownames": np.array(cd_rn), "cd_sample_type": np.array(cd["sample_type"], dtype=str),
           "cd_cell_number": np.array(cd["cell_number"]).astype(str), "cd_cell_type": np.array(cd["cell_type"], dtype=str)}
    for b in BATCHES:
        a = f"proteins_{b}_norm_log"
        sce = assays[a]
        m, dim = sce_matrix(sce)
        X = np.asarray(m.value, dtype=float).reshape(dim[1], dim[0]).T
        names = sce.attr.get("NAMES")
        if names is not None and names.type == 16 and names.value is not None:
            rows = names.value
        elif m.attr.get("dimnames") is not None and m.attr["dimnames"].value[0] is not None:
            rows = m.attr["dimnames"].value[0].value
        else:  # names live in rowRanges@partitioning@NAMES
            rows = sce.attr["rowRanges"].attr["partitioning"].attr["NAMES"].value
        assert len(rows) == X.shape[0] and all(isinstance(r, str) for r in rows), a
        cols = sce.attr["colData"].attr["rownames"].value
        k = np.array(sm["assay"]) == a
        c2p = dict(zip(np.array(sm["colname"])[k], np.array(sm["primary"])[k]))
        res[f"X_{b}"] = X
        res[f"rows_{b}"] = np.array(rows)
        res[f"primary_{b}"] = np.array([c2p.get(c, "") for c in cols])
        print(a, X.shape, "NaN", round(float(np.isnan(X).mean()), 3))
    np.savez_compressed(out, **res)


def build(npz):
    d = np.load(npz)
    ok = {r for r, t, n in zip(d["cd_rownames"], d["cd_sample_type"], d["cd_cell_number"]) if t == "SC" and n == "1"}
    frames = []
    for b in BATCHES:
        keep = np.array([p in ok for p in d[f"primary_{b}"]])
        frames.append(pd.DataFrame(d[f"X_{b}"][:, keep].T, columns=d[f"rows_{b}"], index=d[f"primary_{b}"][keep]))
    P = pd.concat(frames, axis=0, join="outer")
    print("kept cells per batch:", [len(f) for f in frames])
    save("gregoire2023_mixCTRL", P.values, [(group_accessions(str(r)) or [""])[0] for r in P.columns])


if __name__ == "__main__":
    if sys.argv[1] == "extract":
        extract(sys.argv[2], sys.argv[3])
    else:
        build(sys.argv[2])
