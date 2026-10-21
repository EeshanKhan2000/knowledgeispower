"""Dataset loaders following the convention: cells=obs, proteins=var, X=log2 (NaN=missing),
layers['raw']=linear intensities."""

from __future__ import annotations

import anndata as ad
import numpy as np
import pandas as pd

from .ids import DATA_DIR
from .registry import register_dataset, validate_dataset

PETROSIUS_PATH = DATA_DIR / "datasets" / "petrosius2023_aml_sc.h5ad"


def from_log2_matrix(X, cells, proteins, obs: pd.DataFrame | None = None) -> ad.AnnData:
    X = np.asarray(X, dtype=float)
    a = ad.AnnData(
        X=X,
        obs=obs.copy() if obs is not None else pd.DataFrame(index=pd.Index(cells, name="cell")),
        var=pd.DataFrame(index=pd.Index(proteins, name="protein")),
    )
    a.obs_names, a.var_names = list(map(str, cells)), list(map(str, proteins))
    a.layers["raw"] = np.exp2(X)  # NaN stays NaN
    validate_dataset(a)
    return a


def load_petrosius2023() -> ad.AnnData:
    """OCI-AML8227 single cells (Orbitrap Astral DIA), 4 FACS-gated populations.

    ``layers['raw']`` is reconstructed as ``2**X`` (the source h5ad ships log2 only).
    Cell ids are shortened to ``<population>_<n>``; the original run name is kept in
    ``obs['run']``.
    """
    src = ad.read_h5ad(PETROSIUS_PATH)
    runs = src.obs_names.to_series()
    short = runs.str.extract(r"sc8227_(.+)\.raw$")[0].fillna(runs)
    obs = pd.DataFrame({"cell_type": src.obs["cell_type"].astype(str).values, "run": runs.values},
                       index=short.values)
    a = from_log2_matrix(np.asarray(src.X, dtype=float), short.values, src.var_names, obs=obs)
    a.uns["dataset"] = dict(src.uns.get("dataset", {}))
    return a


register_dataset("petrosius2023", load_petrosius2023,
                 "OCI-AML8227 single-cell proteomics (Petrosius et al. 2023 preprint), 215 cells", contrib=False)
