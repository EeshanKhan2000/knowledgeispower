"""IntAct molecular interactions (human-human), from the clustered MITAB file.

Raw file: ``data/cache/reps/intact/intact-micluster.zip`` (IntAct ``current/psimitab/``;
one row per unique interactor pair with all its evidences merged; MITAB 2.7 columns). It is used instead of the 1.1 GB
``species/human.zip`` (evidence-level MITAB 2.7) because it is smaller (893 MB) and already
aggregated per pair; both sides are filtered to taxid 9606 here anyway.

In this file the primary ``ID(s) interactor`` columns hold IntAct ``intact:EBI-...`` IDs and the UniProt
accession is in ``Alt. ID(s) interactor``; the first ``uniprotkb:`` token of the primary column, else
of the alt-ID column, is used (alias columns, which list secondary accessions, are ignored).

Kept rows: both interactors have a ``uniprotkb:`` accession (isoform / ``-PRO_`` chain
suffixes collapsed to the canonical accession), both taxid columns are ``taxid:9606``, the pair is
not a self-interaction, and the row's interaction types are not *only* colocalization (MI:0403) or
genetic interaction (MI:0208 and children named "... genetic interaction"), so the graph stays
comparable to the BioGRID physical graph.

Edge weight = number of distinct publications: distinct ``pubmed:`` IDs in the publication column;
a row with no PubMed ID but some other publication identifier contributes its first identifier.
Rows that collapse to the same canonical pair (isoforms) have their publication sets merged.
"""

from __future__ import annotations

import io
import zipfile
from functools import lru_cache

import networkx as nx
import numpy as np

from ..features import spectral_block
from ..ids import canonical_accession
from ._kbutil import cache_fresh, graph_from_edges, load_edges, read_meta, save_edges, source_dir, write_meta

NAME = "intact"
URL = "https://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/intact-micluster.zip"
DIR = source_dir(NAME)
RAW = DIR / "intact-micluster.zip"
EDGES = DIR / "derived_human_edges.npz"
META = DIR / "derived_meta.json"


def _uniprot(field: str) -> str | None:
    for tok in field.split("|"):
        if tok.startswith("uniprotkb:"):
            return canonical_accession(tok[len("uniprotkb:"):])
    return None


def _human(field: str) -> bool:
    return any(t.split("(")[0] == "taxid:9606" for t in field.split("|"))


def _non_physical_only(types: str) -> bool:
    toks = [t for t in types.split("|") if t and t != "-"]
    if not toks:
        return False
    return all("MI:0403" in t or "MI:0208" in t or "genetic interaction" in t for t in toks)


def _pubs(field: str) -> set[str]:
    toks = [t for t in field.split("|") if t and t != "-"]
    pm = {t for t in toks if t.startswith("pubmed:")}
    return pm if pm else set(toks[:1])


def _build() -> None:
    pubs: dict[tuple[str, str], set[str]] = {}
    n_rows = n_kept = n_nonphys = 0
    with zipfile.ZipFile(RAW) as z:
        members = [n for n in z.namelist() if n.endswith(".txt") and "negative" not in n]
        if len(members) != 1:
            raise RuntimeError(f"expected one MITAB member in {RAW.name}, found {members}")
        member = members[0]
        with z.open(member) as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
                if line.startswith("#"):
                    continue
                n_rows += 1
                f = line.rstrip("\n").split("\t")
                if len(f) < 15 or not (_human(f[9]) and _human(f[10])):
                    continue
                a, b = _uniprot(f[0]) or _uniprot(f[2]), _uniprot(f[1]) or _uniprot(f[3])
                if not a or not b or a == b:
                    continue
                if _non_physical_only(f[11]):
                    n_nonphys += 1
                    continue
                pp = _pubs(f[8])
                if not pp:
                    continue
                n_kept += 1
                # several clustered rows can collapse to one canonical pair (isoforms): union the publications
                pubs.setdefault((a, b) if a < b else (b, a), set()).update(pp)
    edges = {k: float(len(v)) for k, v in pubs.items()}
    save_edges(EDGES, edges)
    write_meta(META, [RAW], url=URL, member=member, n_rows=n_rows, n_rows_kept=n_kept,
               n_rows_non_physical_only=n_nonphys, n_edges=len(edges))


@lru_cache(maxsize=1)
def _edges():
    if not (EDGES.exists() and cache_fresh(META, [RAW])):
        _build()
    return load_edges(EDGES)


def provenance() -> dict:
    _edges()
    m = read_meta(META)
    return {"source": "IntAct (micluster)", "url": URL, "member": m["member"], "raw": m["raw"]}


def graph(var_names) -> nx.Graph:
    nodes, i, j, w = _edges()
    return graph_from_edges(var_names, nodes, i, j, w, provenance())


def block(var_names, d: int = 16) -> np.ndarray:
    return spectral_block(graph(var_names), var_names, d)
