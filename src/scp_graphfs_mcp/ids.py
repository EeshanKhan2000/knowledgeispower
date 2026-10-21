"""Protein / gene identifier handling.

All graph nodes are keyed by **canonical UniProt accessions** (isoform suffix
``-N`` and processed-chain suffix ``-PRO_...`` stripped). Dataset features are
often *protein groups* (``"P1;P2;P3"``); a group maps to the set of its
canonical accessions and is treated as a member of a complex if **any** of its
accessions is.

Gene symbols are resolved through the HGNC snapshot in ``data/raw`` (current
symbol, alias symbols, previous symbols, Ensembl gene IDs). No network access.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
HGNC_PATH = DATA_DIR / "raw" / "hgnc_complete_set.txt"

# Official UniProt accession pattern (https://www.uniprot.org/help/accession_numbers)
UNIPROT_RE = re.compile(
    r"(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})"
)
_UNIPROT_FULL_RE = re.compile(rf"^{UNIPROT_RE.pattern}(?:-\d+|-PRO_\d+)?$")


def canonical_accession(acc: str) -> str | None:
    """``'P28074-2'`` -> ``'P28074'``; returns ``None`` if not a UniProt accession."""
    acc = acc.strip()
    if not _UNIPROT_FULL_RE.match(acc):
        return None
    return acc.split("-")[0]


def extract_accessions(text: str) -> list[str]:
    """All canonical UniProt accessions found in a free-text field, in order, deduplicated."""
    seen: dict[str, None] = {}
    for tok in re.split(r"[\s;,|\[\]()]+", text or ""):
        c = canonical_accession(tok)
        if c:
            seen.setdefault(c, None)
    return list(seen)


def group_accessions(feature_id: str) -> list[str]:
    """Protein-group feature id (``'P1;P2-2'``) -> canonical accessions ``['P1', 'P2']``."""
    return extract_accessions(feature_id.replace(";", " "))


@lru_cache(maxsize=1)
def hgnc_table() -> pd.DataFrame:
    """HGNC complete set (approved symbols only)."""
    df = pd.read_csv(HGNC_PATH, sep="\t", dtype=str, low_memory=False).fillna("")
    return df[df["status"] == "Approved"].reset_index(drop=True)


@lru_cache(maxsize=1)
def _symbol_indices() -> dict[str, dict[str, set[str]]]:
    df = hgnc_table()
    idx: dict[str, dict[str, set[str]]] = {
        "symbol": {},
        "alias": {},
        "prev": {},
        "ensembl": {},
        "uniprot_of": {},
        "symbol_of_acc": {},
    }
    for row in df.itertuples(index=False):
        sym = row.symbol
        idx["symbol"].setdefault(sym.upper(), set()).add(sym)
        for a in filter(None, row.alias_symbol.split("|")):
            idx["alias"].setdefault(a.upper(), set()).add(sym)
        for p in filter(None, row.prev_symbol.split("|")):
            idx["prev"].setdefault(p.upper(), set()).add(sym)
        if row.ensembl_gene_id:
            idx["ensembl"].setdefault(row.ensembl_gene_id, set()).add(sym)
        accs = set(extract_accessions(row.uniprot_ids.replace("|", " ")))
        idx["uniprot_of"][sym] = accs
        for acc in accs:
            idx["symbol_of_acc"].setdefault(acc, set()).add(sym)
    return idx


def resolve_symbol(query: str) -> tuple[list[str], str]:
    """Resolve a gene symbol / alias / previous symbol / Ensembl gene ID to current HGNC symbol(s).

    Returns ``(symbols, how)`` where ``how`` is one of ``'symbol'``, ``'ensembl'``,
    ``'prev'``, ``'alias'`` or ``'unresolved'``. Current symbols win over previous
    symbols, which win over aliases; ambiguity is returned, never guessed away.
    """
    idx = _symbol_indices()
    q = query.strip()
    if q.upper().startswith("ENSG"):
        hit = idx["ensembl"].get(q.split(".")[0], set())
        return sorted(hit), "ensembl" if hit else "unresolved"
    for how in ("symbol", "prev", "alias"):
        hit = idx[how].get(q.upper())
        if hit:
            return sorted(hit), how
    return [], "unresolved"


def uniprot_for_symbol(symbol: str) -> list[str]:
    """Canonical UniProt accessions HGNC lists for a current symbol."""
    return sorted(_symbol_indices()["uniprot_of"].get(symbol, set()))


def symbols_for_accession(acc: str) -> list[str]:
    c = canonical_accession(acc)
    return sorted(_symbol_indices()["symbol_of_acc"].get(c, set())) if c else []


def map_features(feature_ids: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Map dataset features to canonical accessions. Returns ``(mapping, unmapped)``."""
    mapping, unmapped = {}, []
    for f in feature_ids:
        accs = group_accessions(f)
        if accs:
            mapping[f] = accs
        else:
            unmapped.append(f)
    return mapping, unmapped
