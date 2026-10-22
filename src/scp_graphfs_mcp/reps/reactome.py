"""Reactome pathway membership (Homo sapiens).

Raw files (``data/cache/reps/reactome/``, see ``scripts/fetch_features.sh``):

* ``UniProt2Reactome_All_Levels.txt``: UniProt -> every pathway in the hierarchy containing it
  (the protein's lowest-level pathways *and* all their ancestors). Used for ``block``.
* ``UniProt2Reactome.txt``: UniProt -> lowest-level pathways only. Used for ``graph``: two proteins
  are linked if they share a lowest-level pathway with <= ``MAX_PATHWAY`` human members; weight =
  number of such shared pathways. Ancestor pathways are excluded from the graph because they are
  large and would link most of the proteome.

Both files are tab-separated without header: accession, stable ID, URL, name, evidence code, species.
Only rows with species ``Homo sapiens`` are kept; all evidence codes (TAS, IEA) are kept. Isoform
accessions (``P12345-2``) are collapsed to the canonical accession.
"""

from __future__ import annotations

import json
from functools import lru_cache

import networkx as nx
import numpy as np

from ..features import _accs, _svd_block, spectral_block
from ..ids import canonical_accession
from ._kbutil import cache_fresh, graph_from_edges, load_edges, read_meta, save_edges, source_dir, write_meta

NAME = "reactome"
URLS = {
    "UniProt2Reactome_All_Levels.txt": "https://reactome.org/download/current/UniProt2Reactome_All_Levels.txt",
    "UniProt2Reactome.txt": "https://reactome.org/download/current/UniProt2Reactome.txt",
}
MAX_PATHWAY = 50
DIR = source_dir(NAME)
RAW_ALL = DIR / "UniProt2Reactome_All_Levels.txt"
RAW_LOW = DIR / "UniProt2Reactome.txt"
SETS = DIR / "derived_human_pathway_sets.json"
EDGES = DIR / "derived_lowest_le50_edges.npz"
META = DIR / "derived_meta.json"


def _read_human(path) -> dict[str, set[str]]:
    idx: dict[str, set[str]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 6 or f[5] != "Homo sapiens":
                continue
            acc = canonical_accession(f[0])
            if acc:
                idx.setdefault(acc, set()).add(f[1])
    return idx


def _build() -> None:
    all_lv = _read_human(RAW_ALL)
    low = _read_human(RAW_LOW)
    members: dict[str, set[str]] = {}
    for acc, pws in low.items():
        for pw in pws:
            members.setdefault(pw, set()).add(acc)
    edges: dict[tuple[str, str], float] = {}
    n_small = 0
    for pw, accs in members.items():
        if len(accs) > MAX_PATHWAY:
            continue
        n_small += 1
        s = sorted(accs)
        for a in range(len(s)):
            for b in range(a + 1, len(s)):
                edges[(s[a], s[b])] = edges.get((s[a], s[b]), 0.0) + 1.0
    SETS.write_text(json.dumps({"all_levels": {k: sorted(v) for k, v in all_lv.items()},
                                "lowest": {k: sorted(v) for k, v in low.items()}}))
    save_edges(EDGES, edges)
    write_meta(META, [RAW_ALL, RAW_LOW], urls=URLS, n_accessions_all_levels=len(all_lv),
               n_accessions_lowest=len(low), n_lowest_pathways=len(members),
               n_lowest_pathways_le_max=n_small, max_pathway=MAX_PATHWAY, n_edges=len(edges))


def _ensure() -> None:
    if not (SETS.exists() and EDGES.exists() and cache_fresh(META, [RAW_ALL, RAW_LOW])):
        _build()


@lru_cache(maxsize=1)
def _sets() -> dict[str, dict[str, set[str]]]:
    _ensure()
    raw = json.loads(SETS.read_text())
    return {lvl: {k: set(v) for k, v in d.items()} for lvl, d in raw.items()}


@lru_cache(maxsize=1)
def _edges():
    _ensure()
    return load_edges(EDGES)


def provenance() -> dict:
    _ensure()
    m = read_meta(META)
    return {"source": "Reactome", "urls": URLS, "raw": m["raw"], "max_pathway": MAX_PATHWAY}


def block(var_names, d: int = 32) -> np.ndarray:
    """SVD embedding of all-levels pathway membership sets (pathways with >= 5 members among var_names)."""
    idx = _sets()["all_levels"]
    return _svd_block([idx.get(a, set()) for a in _accs(var_names)], vocab_min=5, d=d)


def graph(var_names) -> nx.Graph:
    """Shared lowest-level pathway (size <= 50) graph; weight = number of shared such pathways."""
    nodes, i, j, w = _edges()
    return graph_from_edges(var_names, nodes, i, j, w, provenance())


def spectral(var_names, d: int = 16) -> np.ndarray:
    return spectral_block(graph(var_names), var_names, d)
