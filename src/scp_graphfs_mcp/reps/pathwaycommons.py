"""Pathway Commons v14 mechanistic graph: the documented fallback for INDRA assembled mechanisms.

Why not INDRA: the INDRA DB S3 dumps (``bigmech`` bucket, ``indra-db/dumps/...``, ``indra_db_sif_dump/...``)
answered 403 to direct object requests on 2026-10-22 (the indra_db code reads them with signed S3 clients),
and the public REST API (https://db.indra.bio/agents/from_agents?agent=<UP>@UP&format=json) works without a
key but takes ~15 s per protein (paginated, 500 agent pairs per page), i.e. many hours for ~7k proteins -
not a reasonable load to put on a public academic service.

Raw files (``scripts/fetch_features.sh``, Amendment 9 section) in ``data/cache/reps/pathwaycommons/``, from
https://download.baderlab.org/PathwayCommons/PC2/v14/ (``www.pathwaycommons.org/archives/PC2/`` redirects
there): ``pc-hgnc.txt.gz`` (extended SIF: ``PARTICIPANT_A, INTERACTION_TYPE, PARTICIPANT_B,
INTERACTION_DATA_SOURCE, INTERACTION_PUBMED_ID, PATHWAY_NAMES, MEDIATOR_IDS``, followed by a participants
section, which is not used) and ``datasources.txt`` (versions of the 20+ integrated databases: Reactome,
PID, PhosphoSitePlus, HumanCyc, HPRD, PANTHER, DIP, BioGRID, IntAct, ...).

Graph: only rows whose two participants are both HGNC symbols that map (current symbol, else an
unambiguous previous symbol / alias, via ``ids.resolve_symbol``) to UniProt (``ids.uniprot_for_symbol``);
chemical participants (CHEBI ids) therefore drop out. All remaining interaction types are kept (undirected).
Edge weight = number of distinct data sources supporting the protein pair (evidence count; >= 1).

Derived cache: ``pc14_edges.npz`` (accession vocabulary, i, j, n_sources, n_pmids).
"""

from __future__ import annotations

import gzip
from functools import lru_cache

import networkx as nx
import numpy as np

from ..features import spectral_block
from ..ids import resolve_symbol, uniprot_for_symbol
from . import _refpanel as rp

NAME = "pathwaycommons"
URL = "https://download.baderlab.org/PathwayCommons/PC2/v14/pc-hgnc.txt.gz"
DIR = rp.REPS_DIR / NAME
RAW = DIR / "pc-hgnc.txt.gz"
CACHE = DIR / "pc14_edges.npz"


def _sym_to_accs(sym: str, memo: dict) -> list[str]:
    if sym not in memo:
        syms, how = resolve_symbol(sym)
        memo[sym] = uniprot_for_symbol(syms[0]) if len(syms) == 1 else []
    return memo[sym]


def _build() -> None:
    memo: dict[str, list[str]] = {}
    src: dict[tuple[str, str], set] = {}
    pm: dict[tuple[str, str], set] = {}
    with gzip.open(RAW, "rt") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        assert header[:5] == ["PARTICIPANT_A", "INTERACTION_TYPE", "PARTICIPANT_B", "INTERACTION_DATA_SOURCE",
                              "INTERACTION_PUBMED_ID"], header
        for line in fh:
            if not line.strip():
                break  # end of the interaction section
            f = line.rstrip("\n").split("\t")
            if f[0] == "PARTICIPANT":
                break
            A, B = _sym_to_accs(f[0], memo), _sym_to_accs(f[2], memo)
            if not A or not B:
                continue
            ds = set(filter(None, f[3].split(";")))
            pmids = set(filter(None, f[4].split(";"))) if len(f) > 4 else set()
            for a in A:
                for b in B:
                    if a == b:
                        continue
                    k = (a, b) if a < b else (b, a)
                    src.setdefault(k, set()).update(ds)
                    pm.setdefault(k, set()).update(pmids)
    vocab = sorted({a for k in src for a in k})
    pos = {a: i for i, a in enumerate(vocab)}
    keys = sorted(src)
    np.savez_compressed(
        CACHE, vocab=np.array(vocab),
        i=np.array([pos[a] for a, _ in keys], np.int32), j=np.array([pos[b] for _, b in keys], np.int32),
        n_sources=np.array([max(1, len(src[k])) for k in keys], np.int32),
        n_pmids=np.array([len(pm[k]) for k in keys], np.int32),
        raw_sha256=np.array(rp.sha256(RAW)),
        n_symbols_seen=np.array(len(memo)), n_symbols_mapped=np.array(sum(bool(v) for v in memo.values())))


@lru_cache(maxsize=1)
def _edges():
    if not CACHE.exists() or CACHE.stat().st_mtime < RAW.stat().st_mtime:
        _build()
    d = np.load(CACHE)
    vocab = [str(a) for a in d["vocab"]]
    return {a: i for i, a in enumerate(vocab)}, d["i"], d["j"], d["n_sources"], str(d["raw_sha256"])


def provenance() -> dict:
    return {"source": "Pathway Commons", "version": "v14 (2024-05-21)", "url": URL, "sha256": _edges()[4]}


@lru_cache(maxsize=8)
def _graph(names: tuple) -> nx.Graph:
    index, I, J, W, _ = _edges()
    rows = rp.align(names, index)
    by_row: dict[int, list[int]] = {}
    for p, r in enumerate(rows):
        if r >= 0:
            by_row.setdefault(int(r), []).append(p)
    g = nx.Graph()
    g.add_nodes_from(names)
    keep = np.isin(I, list(by_row)) & np.isin(J, list(by_row))
    for a, b, w in zip(I[keep], J[keep], W[keep]):
        for u in by_row[int(a)]:
            for v in by_row[int(b)]:
                if u != v:
                    g.add_edge(names[u], names[v], weight=float(w))
    g.graph["provenance"] = {**provenance(), "construction": "HGNC->UniProt, all gene-gene interaction types, weight = #data sources"}
    return g


def graph(var_names) -> nx.Graph:
    """Pathway Commons v14 protein-protein graph over var_names (all added as nodes); weight = #sources."""
    return _graph(tuple(str(v) for v in var_names)).copy()


def block(var_names, d: int = 16) -> np.ndarray:
    """Laplacian-eigenmap embedding of ``graph(var_names)`` (features.spectral_block) + has column."""
    names = [str(v) for v in var_names]
    return spectral_block(_graph(tuple(names)), names, d)
