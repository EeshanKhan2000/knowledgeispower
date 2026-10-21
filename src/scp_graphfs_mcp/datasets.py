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


LEDUC_PATH = DATA_DIR / "datasets" / "leduc2022_pscope_proteins_norm2.h5ad"


def load_leduc2022() -> ad.AnnData:
    """Leduc et al. 2022 (nPOP / pSCoPE) melanoma + monocyte single cells; the pre-imputation protein
    assay `proteins_norm2` (log2 relative quantities, NaN = missing). Held out for the phase-3
    independent-dataset confirmation; see benchmarks/EXPLORATION.md."""
    a = ad.read_h5ad(LEDUC_PATH)
    validate_dataset(a)
    return a


SPECHT_PATH = DATA_DIR / "datasets" / "specht2021_scope2_proteins_from_peptides.h5ad"


def load_specht2021() -> ad.AnnData:
    """SCoPE2 macrophages/monocytes (Specht et al. 2021); proteins = median of unimputed peptides.
    Held out for the v5 confirmation; see benchmarks/EXPLORATION.md Amendment 3."""
    a = ad.read_h5ad(SPECHT_PATH)
    validate_dataset(a)
    return a


register_dataset("specht2021", load_specht2021,
                 "SCoPE2 macrophage/monocyte, proteins aggregated from unimputed peptides (held-out dataset)", contrib=False)
register_dataset("leduc2022", load_leduc2022,
                 "Leduc et al. 2022 pSCoPE melanoma/monocyte, pre-imputation proteins (held-out dataset)", contrib=False)
register_dataset("petrosius2023", load_petrosius2023,
                 "OCI-AML8227 single-cell proteomics (Petrosius et al. 2023 preprint), 215 cells", contrib=False)
