"""BioGRID physical protein-protein interactions (Homo sapiens).

Raw file: ``data/cache/reps/biogrid/BIOGRID-ORGANISM-LATEST.tab3.zip`` (the ``Homo_sapiens`` TAB3
member is read; its file name carries the BioGRID release, e.g. ``...-5.0.262.tab3.txt``).

Kept rows: ``Experimental System Type == physical`` and both ``Organism ID`` == 9606. Interactors
are mapped to UniProt through the ``SWISS-PROT Accessions`` columns (``|``-separated; all listed
accessions are used); if that column is ``-``, the Entrez Gene ID is mapped through HGNC
(``entrez_id`` -> ``uniprot_ids``). Self-interactions are dropped.

Edge weight = number of distinct publications (``Publication Source``, e.g. ``PUBMED:9006895``)
supporting the unordered accession pair.
"""

from __future__ import annotations

import io
import zipfile
from functools import lru_cache

import networkx as nx
import numpy as np
import pandas as pd

from ..features import spectral_block
from ..ids import extract_accessions
from ._kbutil import (cache_fresh, entrez_to_uniprot, graph_from_edges, load_edges, read_meta, save_edges,
                      source_dir, write_meta)

NAME = "biogrid"
URL = "https://downloads.thebiogrid.org/Download/BioGRID/Latest-Release/BIOGRID-ORGANISM-LATEST.tab3.zip"
DIR = source_dir(NAME)
RAW = DIR / "BIOGRID-ORGANISM-LATEST.tab3.zip"
EDGES = DIR / "derived_human_physical_edges.npz"
META = DIR / "derived_meta.json"

_COLS = ["Entrez Gene Interactor A", "Entrez Gene Interactor B", "Experimental System Type",
         "Publication Source", "Organism ID Interactor A", "Organism ID Interactor B",
         "SWISS-PROT Accessions Interactor A", "SWISS-PROT Accessions Interactor B"]


def _member(z: zipfile.ZipFile) -> str:
    names = [n for n in z.namelist() if "Homo_sapiens" in n and n.endswith(".tab3.txt")]
    if len(names) != 1:
        raise RuntimeError(f"expected one Homo_sapiens tab3 member, found {names}")
    return names[0]


def _build() -> None:
    e2u = entrez_to_uniprot()

    def accs(sp_col: str, entrez: str) -> tuple[str, ...]:
        if sp_col and sp_col != "-":
            a = tuple(extract_accessions(sp_col.replace("|", " ")))
            if a:
                return a
        return e2u.get(entrez, ())

    pubs: dict[tuple[str, str], set[str]] = {}
    n_rows = n_kept = n_unmapped = 0
    with zipfile.ZipFile(RAW) as z:
        member = _member(z)
        with z.open(member) as fh:
            reader = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8"), sep="\t", usecols=_COLS, dtype=str,
                                 chunksize=500_000, quoting=3, na_filter=False)
            for ch in reader:
                n_rows += len(ch)
                ch = ch[(ch["Experimental System Type"] == "physical")
                        & (ch["Organism ID Interactor A"] == "9606") & (ch["Organism ID Interactor B"] == "9606")]
                n_kept += len(ch)
                for ea, eb, pa, pb, pub in zip(ch["Entrez Gene Interactor A"], ch["Entrez Gene Interactor B"],
                                               ch["SWISS-PROT Accessions Interactor A"],
                                               ch["SWISS-PROT Accessions Interactor B"], ch["Publication Source"]):
                    A, B = accs(pa, ea), accs(pb, eb)
                    if not A or not B:
                        n_unmapped += 1
                        continue
                    for a in A:
                        for b in B:
                            if a != b:
                                pubs.setdefault((a, b) if a < b else (b, a), set()).add(pub)
    edges = {k: float(len(v)) for k, v in pubs.items()}
    save_edges(EDGES, edges)
    write_meta(META, [RAW], url=URL, member=member, n_rows=n_rows, n_physical_human=n_kept,
               n_rows_unmapped=n_unmapped, n_edges=len(edges))


@lru_cache(maxsize=1)
def _edges():
    if not (EDGES.exists() and cache_fresh(META, [RAW])):
        _build()
    return load_edges(EDGES)


def provenance() -> dict:
    _edges()
    m = read_meta(META)
    return {"source": "BioGRID", "url": URL, "member": m["member"], "raw": m["raw"]}


def graph(var_names) -> nx.Graph:
    nodes, i, j, w = _edges()
    return graph_from_edges(var_names, nodes, i, j, w, provenance())


def block(var_names, d: int = 16) -> np.ndarray:
    return spectral_block(graph(var_names), var_names, d)
