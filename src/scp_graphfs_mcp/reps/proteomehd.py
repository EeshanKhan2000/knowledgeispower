"""ProteomeHD reference panel (Kustatscher et al. 2019, Nat Biotechnol): 10,323 human proteins x 294 SILAC
log2 H/L ratio experiments, plus the published pairwise co-regulation scores (treeClust similarity ->
sigmoid -> topological overlap) for the 5,013 proteins with enough observations (12,562,578 pairs).

Raw files (``scripts/fetch_features.sh``, Amendment 9 section), all in ``data/cache/reps/proteomehd/``:

* ``ProteomeHD_v1_1.7z`` -> ``ProteomeHD_v1_1.csv`` from GitHub ``Rappsilber-Laboratory/ProteomeHD``
  ``Data/`` (commit 2ee6d87110b9d4932af0d106927eb289dfbce321; the README says it is an exact copy of
  Supplementary Table S1). Columns: ``Majority_protein_IDs, Simplified_protein_ID, Protein_names,
  Gene_names`` + 294 SILAC ratio columns (values as provided, centred near 0) (264 ``RatioHL_*``, 30 ``RatioML_*``; empty = missing).
* ``coregulation_scores.zip`` (``coregulation_scores.csv``: ``Protein_1, Protein_2, coregulation_score``,
  proteins named by their Majority_protein_IDs string) from PRIDE PXD008888.

Alignment: a panel row is indexed under every canonical accession of its Majority_protein_IDs (the
Simplified_protein_ID takes precedence when an accession occurs in several rows).

Derived cache: ``proteomehd_matrix.npz`` (accs index, X float32 proteins x experiments) and
``proteomehd_coreg.npz`` (dense float32 co-regulation score matrix over the scored proteins, row ids = panel
rows). API: ``reference``, ``corr_graph`` (co-regulation scores by default), ``block``.
"""

from __future__ import annotations

import zipfile
from functools import lru_cache

import networkx as nx
import numpy as np
import pandas as pd

from ..features import _finish
from ..ids import canonical_accession, group_accessions
from . import _refpanel as rp

NAME = "proteomehd"
URL_MATRIX = "https://github.com/Rappsilber-Laboratory/ProteomeHD/raw/2ee6d87110b9d4932af0d106927eb289dfbce321/Data/ProteomeHD_v1_1.7z"
URL_COREG = "https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/11/PXD008888/coregulation_scores.zip"
DIR = rp.REPS_DIR / NAME
RAW_CSV = DIR / "ProteomeHD_v1_1.csv"     # extracted from ProteomeHD_v1_1.7z (fetch script)
RAW_7Z = DIR / "ProteomeHD_v1_1.7z"
RAW_COREG = DIR / "coregulation_scores.zip"
CACHE = DIR / "proteomehd_matrix.npz"
CACHE_COREG = DIR / "proteomehd_coreg.npz"
MIN_SHARED = 30   # pearson corr_graph: minimum shared experiments
MIN_OBS = 30      # block: minimum observed experiments for a protein to enter the SVD


def _build_matrix() -> None:
    df = pd.read_csv(RAW_CSV)
    ratio_cols = [c for c in df.columns if c.startswith(("RatioHL_", "RatioML_", "RatioHM_"))]
    X = df[ratio_cols].to_numpy(np.float32)
    labels = df["Majority_protein_IDs"].astype(str).to_numpy()
    index: dict[str, int] = {}
    for i, s in enumerate(df["Simplified_protein_ID"].astype(str)):
        c = canonical_accession(s)
        if c and c not in index:
            index[c] = i
    for i, lab in enumerate(labels):
        for a in group_accessions(lab):
            index.setdefault(a, i)
    keys = sorted(index)
    np.savez_compressed(CACHE, X=X, labels=labels.astype(str), experiments=np.array(ratio_cols),
                        idx_acc=np.array(keys), idx_row=np.array([index[k] for k in keys]),
                        raw_sha256=np.array(rp.sha256(RAW_7Z) if RAW_7Z.exists() else rp.sha256(RAW_CSV)))


@lru_cache(maxsize=1)
def _panel():
    if not CACHE.exists():
        _build_matrix()
    d = np.load(CACHE, allow_pickle=False)
    index = {str(a): int(r) for a, r in zip(d["idx_acc"], d["idx_row"])}
    return d["X"].astype(float), index, [str(x) for x in d["labels"]], str(d["raw_sha256"])


def _build_coreg() -> None:
    _, _, labels, _ = _panel()
    row_of = {lab: i for i, lab in enumerate(labels)}
    scored: dict[str, int] = {}
    parts = []
    with zipfile.ZipFile(RAW_COREG) as z, z.open("coregulation_scores.csv") as fh:
        for chunk in pd.read_csv(fh, chunksize=2_000_000, dtype={"Protein_1": str, "Protein_2": str,
                                                                    "coregulation_score": np.float32}):
            a = np.array([scored.setdefault(s, len(scored)) for s in chunk["Protein_1"]], np.int32)
            b = np.array([scored.setdefault(s, len(scored)) for s in chunk["Protein_2"]], np.int32)
            parts.append((a, b, chunk["coregulation_score"].to_numpy(np.float32)))
    n = len(scored)
    S = np.full((n, n), np.nan, np.float32)
    for a, b, v in parts:
        S[a, b] = v
        S[b, a] = v
    names = sorted(scored, key=scored.get)
    missing = [s for s in names if s not in row_of]
    if missing:
        raise ValueError(f"{len(missing)} co-regulation protein ids not found in ProteomeHD_v1_1.csv, e.g. {missing[:3]}")
    np.savez(CACHE_COREG, S=S, rows=np.array([row_of[s] for s in names], np.int32),
             raw_sha256=np.array(rp.sha256(RAW_COREG)))


@lru_cache(maxsize=1)
def _coreg():
    if not CACHE_COREG.exists():
        _build_coreg()
    d = np.load(CACHE_COREG)
    return d["S"], d["rows"], str(d["raw_sha256"])


def provenance() -> dict:
    return {"source": "ProteomeHD (Kustatscher et al. 2019)", "version": "v1_1", "url": URL_MATRIX,
            "sha256": _panel()[3]}


def reference(var_names):
    """(p x 294) per-protein standardised ProteomeHD SILAC ratios aligned to var_names, has mask."""
    X, index, _, _ = _panel()
    return rp.reference(var_names, X, index)


def corr_graph(var_names, top: int = 20, method: str = "coregulation", min_shared: int = MIN_SHARED) -> nx.Graph:
    """Each protein linked to its `top` highest-scoring partners; weight = score.

    method="coregulation" (default): the published ProteomeHD co-regulation scores (only the 5,013 scored
    proteins can get edges). method="pearson": pairwise-complete Pearson over the 294 experiments
    (>= `min_shared` shared experiments, r > 0)."""
    X, index, _, _ = _panel()
    rows = rp.align(var_names, index)
    if method == "pearson":
        idx = np.flatnonzero(rows >= 0)
        r, n = rp.pairwise_corr(X[rows[idx]])
        g = rp.knn_graph(var_names, rows, r, top, valid=n >= min_shared)
        g.graph["provenance"] = {**provenance(), "construction": f"top-{top} pairwise Pearson, >= {min_shared} experiments"}
        return g
    if method != "coregulation":
        raise ValueError(method)
    S, srows, sha = _coreg()
    pos = np.full(len(_panel()[2]), -1, int)
    pos[srows] = np.arange(len(srows))
    sidx = np.where(rows >= 0, pos[np.maximum(rows, 0)], -1)   # var_name -> row of S (or -1)
    ok = np.flatnonzero(sidx >= 0)
    rows_s = np.full(len(rows), -1, int)
    rows_s[ok] = sidx[ok]
    sub = S[np.ix_(sidx[ok], sidx[ok])].astype(float)
    g = rp.knn_graph(var_names, rows_s, sub, top)
    g.graph["provenance"] = {"source": "ProteomeHD co-regulation scores (Kustatscher et al. 2019)",
                             "version": "PXD008888 coregulation_scores.csv", "url": URL_COREG, "sha256": sha,
                             "construction": f"top-{top} co-regulation score"}
    return g


@lru_cache(maxsize=4)
def _loadings(d: int):
    X, _, _, _ = _panel()
    return rp.svd_loadings(X, d, MIN_OBS)


def block(var_names, d: int = 24) -> np.ndarray:
    """SVD loadings (d) of the standardised ProteomeHD ratio matrix (fit on all proteins with >= 30 observed
    experiments, NaN -> 0 after standardisation) + has column."""
    _, index, _, _ = _panel()
    L, ok = _loadings(d)
    rows = rp.align(var_names, index)
    has = np.zeros(len(rows), bool)
    has[rows >= 0] = ok[rows[rows >= 0]]
    M = np.zeros((len(rows), L.shape[1]))
    M[has] = L[rows[has]]
    return _finish(M, has)
