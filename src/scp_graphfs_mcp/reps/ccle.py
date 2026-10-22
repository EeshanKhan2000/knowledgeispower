"""CCLE bulk proteomics reference panel (Nusinow et al. 2020; 375 cancer cell lines, TMT 10-plex).

Raw file (download with ``scripts/fetch_features.sh``, Amendment 9 section):
``data/cache/reps/ccle/protein_quant_current_normalized.csv.gz`` from
https://gygi.hms.harvard.edu/data/ccle/protein_quant_current_normalized.csv.gz

File layout (verified 2026-10-22): 6 id columns (``Protein_Id, Gene_Symbol, Description, Group_ID, Uniprot,
Uniprot_Acc``), 42 ``TenPxNN_Peptides`` columns (peptide counts per 10-plex; excluded), then 378 abundance
columns ``<CELLLINE>_<TISSUE>_TenPxNN`` (normalised relative log abundances, ``NA`` = missing). No bridge-
channel abundance columns remain in this file; three lines (CAL120_BREAST, HCT15_LARGE_INTESTINE,
SW948_LARGE_INTESTINE) appear in two plexes and are averaged (nanmean) -> 375 lines.
Rows: 12,755 protein entries; isoform entries (``P54821-2``) are folded to the canonical accession, keeping
for each canonical accession the entry with the most observed lines (ties: the non-isoform entry).

Derived cache: ``data/cache/reps/ccle/ccle_matrix.npz`` (accs, lines, X float32 proteins x lines, raw sha256).

API: ``reference(var_names) -> (R, has)``, ``corr_graph(var_names, top=20)``, ``block(var_names, d=24)``.
See ``_refpanel`` for alignment / standardisation / SVD conventions.
"""

from __future__ import annotations

import gzip
import warnings
from functools import lru_cache

import networkx as nx
import numpy as np
import pandas as pd

from ..features import _finish
from ..ids import canonical_accession
from . import _refpanel as rp

NAME = "ccle"
URL = "https://gygi.hms.harvard.edu/data/ccle/protein_quant_current_normalized.csv.gz"
DIR = rp.REPS_DIR / NAME
RAW = DIR / "protein_quant_current_normalized.csv.gz"
CACHE = DIR / "ccle_matrix.npz"
MIN_SHARED = 50   # corr_graph: minimum lines observed for both proteins
MIN_OBS = 50      # block: minimum observed lines for a protein to enter the SVD


def _build() -> None:
    with gzip.open(RAW, "rt") as fh:
        header = pd.read_csv(fh, nrows=0).columns.tolist()
    data_cols = [c for c in header[6:] if "_TenPx" in c and not c.endswith("_Peptides")]
    df = pd.read_csv(RAW, usecols=["Uniprot_Acc"] + data_cols, dtype={c: np.float32 for c in data_cols})
    lines = sorted({c.rsplit("_TenPx", 1)[0] for c in data_cols})
    col_of = {ln: [c for c in data_cols if c.rsplit("_TenPx", 1)[0] == ln] for ln in lines}
    X = np.empty((len(df), len(lines)), np.float32)
    with warnings.catch_warnings():  # all-NaN rows in nanmean are expected (protein missing in that line)
        warnings.simplefilter("ignore", RuntimeWarning)
        for j, ln in enumerate(lines):
            X[:, j] = np.nanmean(df[col_of[ln]].to_numpy(np.float32), 1)
    acc_raw = df["Uniprot_Acc"].astype(str).tolist()
    nobs = (~np.isnan(X)).sum(1)
    best: dict[str, tuple] = {}
    for i, a in enumerate(acc_raw):
        c = canonical_accession(a)
        if c is None:
            continue
        key = (int(nobs[i]), a == c)
        if c not in best or key > best[c][0]:
            best[c] = (key, i)
    accs = sorted(best)
    rows = [best[a][1] for a in accs]
    np.savez_compressed(CACHE, accs=np.array(accs), lines=np.array(lines), X=X[rows],
                        raw_sha256=np.array(rp.sha256(RAW)), url=np.array(URL))


@lru_cache(maxsize=1)
def _panel():
    if not CACHE.exists() or CACHE.stat().st_mtime < RAW.stat().st_mtime:
        _build()
    d = np.load(CACHE)
    accs = [str(a) for a in d["accs"]]
    return d["X"].astype(float), {a: i for i, a in enumerate(accs)}, [str(x) for x in d["lines"]], str(d["raw_sha256"])


def provenance() -> dict:
    return {"source": "CCLE proteomics (Nusinow et al. 2020)", "version": "protein_quant_current_normalized",
            "url": URL, "sha256": _panel()[3]}


def reference(var_names):
    """(p x 375) per-protein standardised CCLE abundances aligned to var_names (NaN where absent), has mask."""
    X, index, _, _ = _panel()
    return rp.reference(var_names, X, index)


def corr_graph(var_names, top: int = 20, min_shared: int = MIN_SHARED) -> nx.Graph:
    """Each protein linked to its `top` most positively correlated partners (pairwise-complete Pearson across
    CCLE lines, >= `min_shared` shared lines); weight = r. Isolated nodes kept."""
    X, index, _, _ = _panel()
    rows = rp.align(var_names, index)
    idx = np.flatnonzero(rows >= 0)
    r, n = rp.pairwise_corr(X[rows[idx]])
    g = rp.knn_graph(var_names, rows, r, top, valid=n >= min_shared)
    g.graph["provenance"] = {**provenance(), "construction": f"top-{top} pairwise-complete Pearson, >= {min_shared} lines"}
    return g


@lru_cache(maxsize=4)
def _loadings(d: int):
    X, _, _, _ = _panel()
    return rp.svd_loadings(X, d, MIN_OBS)


def block(var_names, d: int = 24) -> np.ndarray:
    """SVD loadings (d) of the standardised CCLE panel (fit on all proteins with >= 50 observed lines,
    NaN -> 0 after standardisation) + has column."""
    _, index, _, _ = _panel()
    L, ok = _loadings(d)
    rows = rp.align(var_names, index)
    has = np.zeros(len(rows), bool)
    has[rows >= 0] = ok[rows[rows >= 0]]
    M = np.zeros((len(rows), L.shape[1]))
    M[has] = L[rows[has]]
    return _finish(M, has)
