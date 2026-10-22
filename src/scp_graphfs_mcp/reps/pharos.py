"""Pharos / TCRD target annotations (NCATS IDG).

Raw: data/cache/reps/pharos/pharos_targets.json, the response of one GraphQL POST to
https://pharos-api.ncats.io/graphql (``dbVersion`` + every target's uniprot, sym, tdl, fam, novelty,
ligandCounts; see scripts/fetch_features.sh). Derived cache: data/cache/reps/pharos/targets.tsv.gz.

``block``: one-hot TDL (Tclin/Tchem/Tbio/Tdark) + one-hot family (fam, 11 levels; missing -> none set),
log10 novelty (missing -> median, with a 0/1 novelty-missing column), log1p ligand and drug counts;
standardised via ``_finish`` with a final has-data column (has = accession is a Pharos target).
"""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from ..features import _accs, _finish
from ..ids import DATA_DIR

REP_DIR = DATA_DIR / "cache" / "reps" / "pharos"
RAW_PATH = REP_DIR / "pharos_targets.json"
DERIVED_PATH = REP_DIR / "targets.tsv.gz"
URL = "https://pharos-api.ncats.io/graphql"
TDLS = ["Tclin", "Tchem", "Tbio", "Tdark"]


@lru_cache(maxsize=1)
def table() -> pd.DataFrame:
    if not DERIVED_PATH.exists():
        with open(RAW_PATH) as fh:
            d = json.load(fh)
        if "errors" in d:
            raise ValueError(f"Pharos response contains errors: {d['errors'][:1]}")
        rows = []
        for t in d["data"]["targets"]["targets"]:
            lc = {c["name"]: c["value"] for c in (t.get("ligandCounts") or [])}
            rows.append({"uniprot": t["uniprot"], "sym": t["sym"], "tdl": t["tdl"], "fam": t["fam"] or "",
                         "novelty": t["novelty"], "ligand": lc.get("ligand", 0), "drug": lc.get("drug", 0)})
        df = pd.DataFrame(rows).drop_duplicates("uniprot")
        df.to_csv(DERIVED_PATH, sep="\t", index=False)
    return pd.read_csv(DERIVED_PATH, sep="\t", dtype={"fam": str}, keep_default_na=False, na_values={"novelty": [""]}).set_index("uniprot")


def block(var_names) -> np.ndarray:
    t = table()
    fams = sorted(f for f in t["fam"].unique() if f)
    accs = _accs(var_names)
    has = np.array([a in t.index for a in accs])
    nov_all = np.log10(t["novelty"].dropna().astype(float))
    med = float(nov_all.median())
    M = np.zeros((len(accs), len(TDLS) + len(fams) + 4))
    for i, a in enumerate(accs):
        if not has[i]:
            continue
        r = t.loc[a]
        if r["tdl"] in TDLS:
            M[i, TDLS.index(r["tdl"])] = 1
        if r["fam"]:
            M[i, len(TDLS) + fams.index(r["fam"])] = 1
        o = len(TDLS) + len(fams)
        nov = r["novelty"]
        M[i, o] = np.log10(nov) if pd.notna(nov) and nov > 0 else med
        M[i, o + 1] = 0.0 if pd.notna(nov) and nov > 0 else 1.0
        M[i, o + 2] = np.log1p(r["ligand"])
        M[i, o + 3] = np.log1p(r["drug"])
    return _finish(M, has)
