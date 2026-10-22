"""Protein feature representations from knowledge sources (EXPLORATION.md Amendment 5).

Every block is a (p x d) float matrix aligned to a dataset's features (first accession of each protein group),
standardised per column, with a final 0/1 "has data" column so missing proteins are explicit rather than
silently zero. Raw sources live in data/cache/features/ (see data/PROVENANCE.md; rebuild with
scripts/fetch_features.sh).
"""

from __future__ import annotations

import gzip
import io
import zipfile
from functools import lru_cache

import networkx as nx
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD

from .ids import DATA_DIR, group_accessions, resolve_symbol, uniprot_for_symbol

FEAT_DIR = DATA_DIR / "cache" / "features"


def _accs(var_names):
    return [(group_accessions(f) or [""])[0] for f in var_names]


def _finish(M: np.ndarray, has: np.ndarray) -> np.ndarray:
    M = np.asarray(M, float)
    if M.size and has.any():
        mu = M[has].mean(0)
        sd = M[has].std(0)
        sd = np.where(sd > 1e-9, sd, 1.0)
        M = np.where(has[:, None], (M - mu) / sd, 0.0)
    return np.hstack([M, has[:, None].astype(float)])


def _svd_block(rows: list[set], vocab_min: int, d: int, seed: int = 0):
    vocab: dict[str, int] = {}
    counts: dict[str, int] = {}
    for r in rows:
        for t in r:
            counts[t] = counts.get(t, 0) + 1
    for t, c in counts.items():
        if c >= vocab_min:
            vocab[t] = len(vocab)
    ii, jj = [], []
    for i, r in enumerate(rows):
        for t in r:
            if t in vocab:
                ii.append(i)
                jj.append(vocab[t])
    has = np.zeros(len(rows), bool)
    has[ii] = True
    if not vocab:
        return _finish(np.zeros((len(rows), 0)), has)
    A = sp.csr_matrix((np.ones(len(ii)), (ii, jj)), shape=(len(rows), len(vocab)))
    A = sp.diags(1 / np.sqrt(np.maximum(np.asarray(A.sum(1)).ravel(), 1))) @ A  # row-normalise
    k = min(d, A.shape[1] - 1, A.shape[0] - 1)
    Z = TruncatedSVD(k, random_state=seed).fit_transform(A) if k >= 1 else np.zeros((len(rows), 0))
    return _finish(Z, has)


# --------------------------------------------------------------------------- sources


@lru_cache(maxsize=1)
def _go_index() -> dict[str, set]:
    idx: dict[str, set] = {}
    with gzip.open(FEAT_DIR / "goa_human.gaf.gz", "rt") as fh:
        for line in fh:
            if line.startswith("!"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) > 6 and "NOT" not in f[3] and f[6] != "ND":
                idx.setdefault(f[1], set()).add(f[4])
    return idx


def go_block(var_names, d: int = 32) -> np.ndarray:
    idx = _go_index()
    return _svd_block([idx.get(a, set()) for a in _accs(var_names)], vocab_min=5, d=d)


@lru_cache(maxsize=1)
def _hpa() -> pd.DataFrame:
    with zipfile.ZipFile(FEAT_DIR / "proteinatlas.tsv.zip") as z:
        name = [n for n in z.namelist() if n.endswith(".tsv")][0]
        df = pd.read_csv(io.BytesIO(z.read(name)), sep="\t", dtype=str).fillna("")
    return df


def hpa_block(var_names, d: int = 24) -> np.ndarray:
    df = _hpa()
    cols = ["Subcellular main location", "Subcellular additional location", "Protein class",
            "RNA tissue specificity", "RNA single cell type specificity", "RNA cell line specificity",
            "Secretome location"]
    idx: dict[str, set] = {}
    for _, r in df.iterrows():
        toks = {f"{c}:{t.strip()}" for c in cols for t in str(r[c]).split(",") if t.strip()}
        for u in str(r["Uniprot"]).split(","):
            if u.strip():
                idx.setdefault(u.strip(), set()).update(toks)
    return _svd_block([idx.get(a, set()) for a in _accs(var_names)], vocab_min=5, d=d)


@lru_cache(maxsize=1)
def _uniprot() -> pd.DataFrame:
    return pd.read_csv(FEAT_DIR / "uniprot_human.tsv", sep="\t", dtype=str).fillna("").set_index("Entry")


def uniprot_keywords_block(var_names, d: int = 24) -> np.ndarray:
    u = _uniprot()
    rows = [set(u.at[a, "Keywords"].split(";")) - {""} if a in u.index else set() for a in _accs(var_names)]
    return _svd_block(rows, vocab_min=5, d=d)


@lru_cache(maxsize=1)
def _paxdb() -> dict[str, float]:
    out: dict[str, float] = {}
    for line in open(FEAT_DIR / "9606-WHOLE_ORGANISM-integrated.txt"):
        if line.startswith("#"):
            continue
        sym, _, ab = line.rstrip("\n").split("\t")[:3]
        s, _ = resolve_symbol(sym)
        if len(s) == 1:
            for acc in uniprot_for_symbol(s[0]):
                out[acc] = float(ab)
    return out


def physical_block(var_names) -> np.ndarray:
    """Structural / physical priors: log PaxDb abundance, log length, log mass (each with its own presence flag)."""
    accs = _accs(var_names)
    pax = _paxdb()
    u = _uniprot()
    ab = np.array([np.log10(pax[a] + 1e-3) if a in pax else np.nan for a in accs])
    ln = np.array([np.log10(float(u.at[a, "Length"])) if a in u.index else np.nan for a in accs])
    ms = np.array([np.log10(float(u.at[a, "Mass"])) if a in u.index and u.at[a, "Mass"] else np.nan for a in accs])
    blocks = []
    for v in (ab, ln, ms):
        has = ~np.isnan(v)
        blocks.append(_finish(np.nan_to_num(v)[:, None], has))
    return np.hstack(blocks)


def spectral_block(graph: nx.Graph, var_names, d: int = 16) -> np.ndarray:
    """Laplacian-eigenmap embedding of a prior graph (isolated proteins -> has=0)."""
    from .methods import adjacency

    A = adjacency(graph, var_names)
    deg = np.asarray(A.sum(1)).ravel()
    has = deg > 0
    if has.sum() <= d + 1:
        return _finish(np.zeros((len(deg), 0)), has)
    Dm = sp.diags(1 / np.sqrt(np.where(has, deg, 1.0)))
    S = Dm @ A @ Dm
    k = min(d, int(has.sum()) - 2)
    vals, vecs = sp.linalg.eigsh(S.astype(float), k=k + 1, which="LA")
    order = np.argsort(-vals)[1:k + 1]  # drop the trivial top eigenvector
    return _finish(vecs[:, order] * np.sqrt(np.maximum(vals[order], 0)), has)


def corpus_loadings_block(var_names, exclude: tuple[str, ...], d: int = 10) -> np.ndarray:
    """'Pretrained' protein loadings: top eigenvectors of the pooled external correlation matrix."""
    from .external import pooled_corr

    R, nds = pooled_corr(var_names, exclude)
    has = (nds > 0).sum(1) > 0
    C = np.nan_to_num(R)
    np.fill_diagonal(C, 1.0)
    vals, vecs = np.linalg.eigh(C)
    order = np.argsort(-vals)[:d]
    return _finish(vecs[:, order] * np.sqrt(np.maximum(vals[order], 0)), has)
