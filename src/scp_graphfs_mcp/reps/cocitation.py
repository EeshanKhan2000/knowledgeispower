"""Literature co-citation graph from NCBI gene2pubmed (Homo sapiens, tax_id 9606).

Raw file: ``data/cache/reps/cocitation/gene2pubmed.gz`` (columns ``#tax_id GeneID PubMed_ID``).

Steps:
1. keep tax_id 9606; map GeneID -> UniProt via HGNC (``entrez_id`` -> ``uniprot_ids``); genes with no
   UniProt accession are dropped *before* paper sizes are counted;
2. drop PubMed IDs that annotate > ``MAX_GENES_PER_PAPER`` (= 100) human genes (high-throughput
   screens / large-scale papers);
3. for every gene pair, ``c`` = number of remaining papers citing both; keep pairs with ``c >= 2``;
4. edge weight = Jaccard ``c / (n_a + n_b - c)`` where ``n`` = number of remaining papers citing the
   gene. Jaccard is used instead of the raw count so heavily studied genes (TP53, EGFR ...) do not
   dominate; the raw count is kept as edge attribute ``count``.

The pairs are computed at Entrez-gene level and then expanded to every UniProt accession HGNC lists
for the gene (if two genes share an accession, the larger weight is kept).
"""

from __future__ import annotations

import gzip
from functools import lru_cache

import networkx as nx
import numpy as np
import scipy.sparse as sp

from ..features import _accs, spectral_block
from ._kbutil import cache_fresh, entrez_to_uniprot, read_meta, source_dir, write_meta

NAME = "cocitation"
URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2pubmed.gz"
MAX_GENES_PER_PAPER = 100
MIN_COCITATIONS = 2
DIR = source_dir(NAME)
RAW = DIR / "gene2pubmed.gz"
EDGES = DIR / "derived_cocitation_edges.npz"
META = DIR / "derived_meta.json"


def _build() -> None:
    e2u = entrez_to_uniprot()
    genes: list[int] = []
    pmids: list[int] = []
    n_human = 0
    with gzip.open(RAW, "rt") as fh:
        for line in fh:
            if not line.startswith("9606\t"):
                continue
            n_human += 1
            _, g, p = line.rstrip("\n").split("\t")
            if g in e2u:
                genes.append(int(g))
                pmids.append(int(p))
    g = np.array(genes, np.int64)
    p = np.array(pmids, np.int64)
    gid, gi = np.unique(g, return_inverse=True)
    pid, pi = np.unique(p, return_inverse=True)
    B = sp.csr_matrix((np.ones(len(gi)), (gi, pi)), shape=(len(gid), len(pid)))
    B.sum_duplicates()
    B.data[:] = 1.0  # duplicate (gene, paper) rows collapse to 1
    paper_size = np.asarray(B.sum(0)).ravel()
    keep = paper_size <= MAX_GENES_PER_PAPER
    B = B[:, np.flatnonzero(keep)].tocsr()
    n_per_gene = np.asarray(B.sum(1)).ravel()
    C = sp.triu(B @ B.T, k=1).tocoo()
    m = C.data >= MIN_COCITATIONS
    r, c, cnt = C.row[m], C.col[m], C.data[m]
    jac = cnt / (n_per_gene[r] + n_per_gene[c] - cnt)
    # expand Entrez -> UniProt
    edges: dict[tuple[str, str], tuple[float, float]] = {}
    for a, b, j, k in zip(gid[r].tolist(), gid[c].tolist(), jac.tolist(), cnt.tolist()):
        for ua in e2u[str(a)]:
            for ub in e2u[str(b)]:
                if ua == ub:
                    continue
                key = (ua, ub) if ua < ub else (ub, ua)
                if key not in edges or edges[key][0] < j:
                    edges[key] = (j, k)
    nodes = sorted({x for e in edges for x in e})
    pos = {x: n for n, x in enumerate(nodes)}
    np.savez_compressed(EDGES, nodes=np.array(nodes, dtype="U12"),
                        i=np.array([pos[a] for a, _ in edges], np.int32),
                        j=np.array([pos[b] for _, b in edges], np.int32),
                        w=np.array([v[0] for v in edges.values()], np.float64),
                        count=np.array([v[1] for v in edges.values()], np.float64))
    write_meta(META, [RAW], url=URL, n_human_rows=n_human, n_rows_mapped=len(gi), n_genes=len(gid),
               n_papers=len(pid), n_papers_kept=int(keep.sum()), max_genes_per_paper=MAX_GENES_PER_PAPER,
               min_cocitations=MIN_COCITATIONS, n_gene_pairs=int(m.sum()), n_edges=len(edges))


@lru_cache(maxsize=1)
def _edges():
    if not (EDGES.exists() and cache_fresh(META, [RAW])):
        _build()
    z = np.load(EDGES, allow_pickle=False)
    return z["nodes"], z["i"], z["j"], z["w"], z["count"]


def provenance() -> dict:
    _edges()
    m = read_meta(META)
    return {"source": "NCBI gene2pubmed co-citation", "url": URL, "raw": m["raw"],
            "max_genes_per_paper": MAX_GENES_PER_PAPER, "min_cocitations": MIN_COCITATIONS, "weight": "jaccard"}


def graph(var_names) -> nx.Graph:
    """Co-citation graph over var_names; ``weight`` = Jaccard, ``count`` = raw co-citation count."""
    nodes, i, j, w, cnt = _edges()
    names = list(var_names)
    g = nx.Graph()
    g.add_nodes_from(names)
    by_acc: dict[str, list[str]] = {}
    for n, a in zip(names, _accs(names)):
        if a:
            by_acc.setdefault(a, []).append(n)
    present = np.isin(nodes, np.array(list(by_acc), dtype=nodes.dtype)) if by_acc else np.zeros(len(nodes), bool)
    m = present[i] & present[j]
    for a, b, x, k in zip(nodes[i[m]].tolist(), nodes[j[m]].tolist(), w[m].tolist(), cnt[m].tolist()):
        for u in by_acc[a]:
            for v in by_acc[b]:
                if u != v:
                    g.add_edge(u, v, weight=float(x), count=float(k))
    g.graph["provenance"] = provenance()
    return g


def block(var_names, d: int = 16) -> np.ndarray:
    return spectral_block(graph(var_names), var_names, d)
