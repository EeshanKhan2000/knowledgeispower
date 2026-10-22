"""PDB co-structure graph from SIFTS: two human proteins are linked if they are chains of the same PDB entry.

Raw: data/cache/reps/pdb_costructure/pdb_chain_uniprot.tsv.gz (SIFTS chain -> UniProt mapping, all PDB).
Rules (fixed before any evaluation):
  * keep only accessions in UniProtKB reviewed human (data/cache/features/uniprot_human.tsv, ``Entry``);
  * an entry contributes pairs only if it has 2..MAX_ACC (=60) distinct human accessions. Larger
    assemblies (full 80S / mito ribosomes, ~180 of ~78k human entries) are dropped so that one giant
    particle does not make a clique of thousands of pairs; their subcomplexes (40S, 60S, proteasome,
    complex I, ...) are deposited separately and stay in;
  * edge ``weight`` = number of shared PDB entries (``graph``); the spectral ``block`` uses log1p(weight)
    so heavily re-solved complexes do not dominate the normalised Laplacian.
Derived cache: data/cache/reps/pdb_costructure/pairs.npz (accession list + upper-triangle pair counts).
"""

from __future__ import annotations

from functools import lru_cache
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd

from ..features import FEAT_DIR, _accs, spectral_block
from ..ids import DATA_DIR

REP_DIR = DATA_DIR / "cache" / "reps" / "pdb_costructure"
RAW_PATH = REP_DIR / "pdb_chain_uniprot.tsv.gz"
DERIVED_PATH = REP_DIR / "pairs.npz"
URL = "https://ftp.ebi.ac.uk/pub/databases/msd/sifts/flatfiles/tsv/pdb_chain_uniprot.tsv.gz"
MAX_ACC = 60


def _build_pairs():
    df = pd.read_csv(RAW_PATH, sep="\t", comment="#", usecols=["PDB", "SP_PRIMARY"], dtype=str)
    human = set(pd.read_csv(FEAT_DIR / "uniprot_human.tsv", sep="\t", usecols=["Entry"], dtype=str)["Entry"])
    df = df[df["SP_PRIMARY"].isin(human)].drop_duplicates()
    acc = np.array(sorted(df["SP_PRIMARY"].unique()))
    pos = {a: i for i, a in enumerate(acc)}
    counts: dict[tuple[int, int], int] = {}
    for _, members in df.groupby("PDB")["SP_PRIMARY"]:
        m = sorted({pos[a] for a in members})
        if 2 <= len(m) <= MAX_ACC:
            for i, j in combinations(m, 2):
                counts[(i, j)] = counts.get((i, j), 0) + 1
    ij = np.array(list(counts.keys()), dtype=np.int32).reshape(-1, 2)
    w = np.array(list(counts.values()), dtype=np.int32)
    np.savez(DERIVED_PATH, acc=acc, i=ij[:, 0], j=ij[:, 1], w=w)


@lru_cache(maxsize=1)
def _pairs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not DERIVED_PATH.exists():
        _build_pairs()
    z = np.load(DERIVED_PATH, allow_pickle=False)
    return z["acc"], z["i"], z["j"], z["w"]


def graph(var_names) -> nx.Graph:
    """Nodes = all var_names strings; edge between two var_names whose first accessions co-occur in >= 1 PDB
    entry, ``weight`` = number of shared entries. Groups sharing a first accession are not self-linked."""
    names = list(var_names)
    acc, I, J, W = _pairs()
    apos = {a: k for k, a in enumerate(acc.tolist())}
    by_acc: dict[int, list[str]] = {}
    for n, a in zip(names, _accs(names)):
        if a in apos:
            by_acc.setdefault(apos[a], []).append(n)
    g = nx.Graph()
    g.add_nodes_from(names)
    keep = np.isin(I, list(by_acc)) & np.isin(J, list(by_acc))
    for i, j, w in zip(I[keep], J[keep], W[keep]):
        for u in by_acc[int(i)]:
            for v in by_acc[int(j)]:
                if u != v:
                    g.add_edge(u, v, weight=float(w))
    g.graph["provenance"] = {"source": "SIFTS pdb_chain_uniprot", "url": URL, "max_accessions_per_entry": MAX_ACC}
    return g


def block(var_names, d: int = 16) -> np.ndarray:
    """Spectral embedding of the co-structure graph restricted to var_names (log1p weights)."""
    g = graph(var_names)
    for _, _, e in g.edges(data=True):
        e["weight"] = float(np.log1p(e["weight"]))
    return spectral_block(g, list(var_names), d=d)
