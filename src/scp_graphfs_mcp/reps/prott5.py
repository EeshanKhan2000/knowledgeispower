"""UniProt precomputed ProtT5 (ProtT5-XL-U50) per-protein embeddings for the human proteome (UP000005640).

Raw: data/cache/reps/prott5/per-protein.h5 (HDF5, one 1024-d float16 dataset per UniProt accession;
UniProt release 2026_03; rebuild with scripts/fetch_features.sh). The PCA used by ``block`` is fit on
*every* protein in the file (~147k Swiss-Prot + TrEMBL entries), never on a dataset, so the
representation is dataset-independent. Derived cache: data/cache/reps/prott5/pca128.npz
(accessions, first 128 PCA scores, PCA mean/components).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from ..features import _accs, _finish
from ..ids import DATA_DIR

REP_DIR = DATA_DIR / "cache" / "reps" / "prott5"
RAW_PATH = REP_DIR / "per-protein.h5"
DERIVED_PATH = REP_DIR / "pca128.npz"
URL = ("https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/embeddings/"
       "UP000005640_9606/per-protein.h5")
N_PCA = 128
DIM = 1024


def _read_all() -> tuple[np.ndarray, np.ndarray]:
    import h5py

    with h5py.File(RAW_PATH, "r") as f:
        keys = sorted(f.keys())
        X = np.empty((len(keys), DIM), np.float32)
        for i, k in enumerate(keys):
            X[i] = f[k][()]
    return np.array(keys), X


@lru_cache(maxsize=1)
def _pca() -> dict:
    if not DERIVED_PATH.exists():
        from sklearn.decomposition import PCA

        keys, X = _read_all()
        pca = PCA(n_components=N_PCA, svd_solver="randomized", random_state=0).fit(X)
        Z = pca.transform(X).astype(np.float32)
        np.savez(DERIVED_PATH, acc=keys, Z=Z, mean=pca.mean_.astype(np.float32),
                 components=pca.components_.astype(np.float32),
                 explained_variance_ratio=pca.explained_variance_ratio_.astype(np.float32))
    z = np.load(DERIVED_PATH, allow_pickle=False)
    out = {k: z[k] for k in z.files}
    out["index"] = {a: i for i, a in enumerate(out["acc"].tolist())}
    return out


def embedding(var_names) -> tuple[np.ndarray, np.ndarray]:
    """Raw (p x 1024) ProtT5 embeddings (first accession per group; zeros where absent) and has-mask."""
    import h5py

    accs = _accs(var_names)
    E = np.zeros((len(accs), DIM), np.float32)
    has = np.zeros(len(accs), bool)
    with h5py.File(RAW_PATH, "r") as f:
        for i, a in enumerate(accs):
            if a and a in f:
                E[i] = f[a][()]
                has[i] = True
    return E, has


def block(var_names, d: int = 32) -> np.ndarray:
    """(p x (d+1)): first d PCA components of the ProtT5 embedding (PCA fit on the whole file), standardised,
    plus a has-data column."""
    if d > N_PCA:
        raise ValueError(f"d <= {N_PCA} supported by the cached PCA")
    P = _pca()
    idx = P["index"]
    rows = np.array([idx.get(a, -1) for a in _accs(var_names)])
    has = rows >= 0
    M = np.zeros((len(rows), d))
    M[has] = P["Z"][rows[has], :d]
    return _finish(M, has)
