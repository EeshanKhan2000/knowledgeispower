"""Curated protein complexes from the CORUM and EBI Complex Portal snapshots in ``data/raw``.

Both sources are normalised into one table with columns
``source, complex_id, name, members`` where ``members`` is a tuple of canonical
UniProt accessions (non-protein participants such as RNA or small molecules are
dropped; Complex Portal sub-complexes are expanded via its
"Expanded participant list" column).
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .ids import DATA_DIR, extract_accessions

CORUM_PATH = DATA_DIR / "raw" / "corum_humanComplexes.txt"
COMPLEX_PORTAL_PATH = DATA_DIR / "raw" / "complexportal_9606.tsv"
SOURCES = ("corum", "complexportal")


@lru_cache(maxsize=1)
def load_corum() -> pd.DataFrame:
    df = pd.read_csv(CORUM_PATH, sep="\t", dtype=str).fillna("")
    out = pd.DataFrame(
        {
            "source": "corum",
            "complex_id": "CORUM:" + df["complex_id"],
            "name": df["complex_name"],
            "members": [tuple(extract_accessions(s)) for s in df["subunits_uniprot_id"]],
        }
    )
    return out[out["members"].map(len) > 0].reset_index(drop=True)


@lru_cache(maxsize=1)
def load_complex_portal() -> pd.DataFrame:
    df = pd.read_csv(COMPLEX_PORTAL_PATH, sep="\t", dtype=str).fillna("")
    expanded = df["Expanded participant list"]
    direct = df["Identifiers (and stoichiometry) of molecules in complex"]
    members = [
        tuple(extract_accessions(e if e and e != "-" else d)) for e, d in zip(expanded, direct)
    ]
    out = pd.DataFrame(
        {
            "source": "complexportal",
            "complex_id": df["#Complex ac"],
            "name": df["Recommended name"],
            "members": members,
        }
    )
    return out[out["members"].map(len) > 0].reset_index(drop=True)


def load_complexes(sources: tuple[str, ...] | list[str] = SOURCES) -> pd.DataFrame:
    loaders = {"corum": load_corum, "complexportal": load_complex_portal}
    unknown = set(sources) - set(loaders)
    if unknown:
        raise ValueError(f"unknown complex source(s): {sorted(unknown)}; choose from {SOURCES}")
    return pd.concat([loaders[s]() for s in sources], ignore_index=True)


@lru_cache(maxsize=4)
def _membership_index(sources: tuple[str, ...]) -> dict[str, list[int]]:
    df = load_complexes(sources)
    idx: dict[str, list[int]] = {}
    for i, mem in enumerate(df["members"]):
        for acc in mem:
            idx.setdefault(acc, []).append(i)
    return idx


def complexes_for_accession(acc: str, sources: tuple[str, ...] = SOURCES) -> pd.DataFrame:
    """All complexes (rows of :func:`load_complexes`) that contain ``acc``."""
    df = load_complexes(sources)
    return df.iloc[_membership_index(tuple(sources)).get(acc, [])]


def in_any_complex(accessions: list[str], sources: tuple[str, ...] = SOURCES) -> bool:
    idx = _membership_index(tuple(sources))
    return any(a in idx for a in accessions)
