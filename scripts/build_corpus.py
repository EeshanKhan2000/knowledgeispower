"""Build the external-evidence corpus (Amendment 4) under data/cache/corpus/ (gitignored; rebuildable).

Each dataset becomes cells x canonical UniProt accessions, log2, per-cell median-centred, NaN = missing:
  petrosius2023, leduc2022, specht2021  - from the committed h5ad snapshots
  schoof2021                            - scpdata schoof2021.Rda, assay `proteins` (gene symbols -> HGNC -> UniProt), single cells only
  woo2022                               - scpdata woo2022_macrophage.Rda, assay `proteins_LFQ` (0 = missing)
The holdouts khan2023 and derks2022 are never part of the corpus.

    python scripts/build_corpus.py <schoof2021_raw.npz> <woo2022.npz>   # .npz from scripts/rda_extract_assay.py
"""
import sys
from pathlib import Path

import numpy as np

from scp_graphfs_mcp.datasets import load_leduc2022, load_petrosius2023, load_specht2021
from scp_graphfs_mcp.ids import group_accessions, resolve_symbol, uniprot_for_symbol

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cache" / "corpus"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, X, accs):
    X = np.asarray(X, float)
    keep_cols = [i for i, a in enumerate(accs) if a]
    X, accs = X[:, keep_cols], [accs[i] for i in keep_cols]
    # collapse duplicate accessions (keep the most-detected column)
    order = np.argsort(-(~np.isnan(X)).sum(0))
    seen, cols = set(), []
    for i in order:
        if accs[i] not in seen:
            seen.add(accs[i]); cols.append(i)
    cols.sort()
    X, accs = X[:, cols], [accs[i] for i in cols]
    X = X[(~np.isnan(X)).sum(1) >= 50]  # drop near-empty cells
    X = X - np.nanmedian(X, axis=1, keepdims=True)
    np.savez_compressed(OUT / f"{name}.npz", X=X.astype(np.float32), accs=np.array(accs))
    print(f"{name}: {X.shape[0]} cells x {X.shape[1]} proteins, missing {np.isnan(X).mean():.3f}")


for name, loader in [("petrosius2023", load_petrosius2023), ("leduc2022", load_leduc2022), ("specht2021", load_specht2021)]:
    a = loader()
    save(name, np.asarray(a.X, float), [(group_accessions(f) or [""])[0] for f in a.var_names])

d = np.load(sys.argv[1])
st = dict(zip(d["cd_rownames"], d["cd_SampleType"]))
sc = np.array([st.get(c, "") == "sc" for c in d["col_primary"]])
X = d["X"][:, sc].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
accs = []
for sym in d["rows"]:
    s, _ = resolve_symbol(str(sym))
    u = uniprot_for_symbol(s[0]) if len(s) == 1 else []
    accs.append(u[0] if u else "")
save("schoof2021", X, accs)

d = np.load(sys.argv[2])
X = d["X"].T
with np.errstate(divide="ignore", invalid="ignore"):
    X = np.where(X > 0, np.log2(X), np.nan)
save("woo2022", X, [(group_accessions(str(r)) or [""])[0] for r in d["rows"]])
