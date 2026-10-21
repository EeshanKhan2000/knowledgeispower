"""Prior graphs over a dataset's protein features, and their degree-preserving shuffled nulls.

Nodes are the dataset's feature ids (protein groups such as ``"P1;P2"`` are allowed;
see :mod:`scp_graphfs_mcp.ids`). Every graph carries
``graph.graph['provenance']`` and ``graph.graph['coverage']``.

* ``corum`` / ``complexportal``: edge = the two proteins share >= 1 complex;
  weight = number of shared complexes.
* ``string``: STRING v12.5 combined score >= ``min_score`` (default 700); weight = score/1000.
* ``string_exp``: STRING **experimental channel only** >= ``min_score``. The combined
  score includes co-expression (leaks the signal we test) and curated databases.
* :func:`shuffled_null`: degree-preserving double-edge swaps (10 x |E| swaps), edge
  weights permuted onto the new edges; seeded.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd

from .complexes import COMPLEX_PORTAL_PATH, CORUM_PATH, load_complexes
from .ids import DATA_DIR, map_features
from .registry import PRIORS, register_prior, validate_prior

STRING_PATH = DATA_DIR / "derived" / "string_v12.5_9606_uniprot.tsv.gz"
N_NULLS = 10

_PROV = {
    "corum": {"source": "CORUM", "version": "current human file (Last-Modified 2026-04-14)",
              "url": "https://mips.helmholtz-muenchen.de/corum/", "path": CORUM_PATH},
    "complexportal": {"source": "EBI Complex Portal", "version": "current (release dir 2026-01-09)",
                      "url": "https://www.ebi.ac.uk/complexportal/", "path": COMPLEX_PORTAL_PATH},
    "string": {"source": "STRING", "version": "12.5", "url": "https://string-db.org/", "path": STRING_PATH},
}


@lru_cache(maxsize=8)
def _sha256(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _provenance(key: str, **extra) -> dict:
    p = dict(_PROV[key])
    p["sha256"] = _sha256(p.pop("path"))
    p.update(extra)
    return p


def _acc_to_features(protein_ids: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    mapping, unmapped = map_features(list(protein_ids))
    inv: dict[str, list[str]] = {}
    for feat, accs in mapping.items():
        for a in accs:
            inv.setdefault(a, []).append(feat)
    return inv, unmapped


def _finish(g: nx.Graph, protein_ids, unmapped, prov) -> nx.Graph:
    n = len(protein_ids)
    g.graph["provenance"] = prov
    g.graph["coverage"] = {
        "n_features": n,
        "n_unmapped": len(unmapped),
        "unmapped_fraction": len(unmapped) / n if n else 0.0,
        "unmapped": list(unmapped),
        "n_with_edges": sum(1 for v in g if g.degree(v) > 0),
        "n_edges": g.number_of_edges(),
    }
    validate_prior(g, list(protein_ids))
    return g


def build_complex_graph(protein_ids: list[str], source: str) -> nx.Graph:
    inv, unmapped = _acc_to_features(protein_ids)
    g = nx.Graph()
    g.add_nodes_from(protein_ids)
    for members in load_complexes((source,))["members"]:
        feats = sorted({f for a in members for f in inv.get(a, [])})
        for u, v in combinations(feats, 2):
            w = g.edges[u, v]["weight"] + 1.0 if g.has_edge(u, v) else 1.0
            g.add_edge(u, v, weight=w)
    return _finish(g, protein_ids, unmapped, _provenance(source))


@lru_cache(maxsize=1)
def _string_edges() -> pd.DataFrame:
    return pd.read_csv(STRING_PATH, sep="\t")


def build_string_graph(protein_ids: list[str], min_score: int = 700, channel: str = "combined") -> nx.Graph:
    if channel not in ("combined", "experimental"):
        raise ValueError("channel must be 'combined' or 'experimental'")
    if not 400 <= min_score <= 1000:
        raise ValueError("min_score must be in [400, 1000] (the derived table keeps scores >= 400)")
    inv, unmapped = _acc_to_features(protein_ids)
    e = _string_edges()
    e = e[(e[channel] >= min_score) & e["a"].isin(inv) & e["b"].isin(inv)]
    g = nx.Graph()
    g.add_nodes_from(protein_ids)
    for a, b, s in zip(e["a"], e["b"], e[channel]):
        for u in inv[a]:
            for v in inv[b]:
                if u != v:
                    w = max(s / 1000.0, g.edges[u, v]["weight"]) if g.has_edge(u, v) else s / 1000.0
                    g.add_edge(u, v, weight=w)
    return _finish(g, protein_ids, unmapped, _provenance("string", channel=channel, min_score=min_score))


def _double_edge_swaps(edges: list[tuple], n_swaps: int, max_tries: int, rng) -> tuple[list[tuple], int]:
    """(a-b, c-d) -> (a-d, c-b) when no self-loop / multi-edge results. Degrees are preserved.

    Same move as ``networkx.double_edge_swap`` but returns how many swaps succeeded
    instead of raising when a dense graph (e.g. CORUM cliques) saturates.
    """
    edges = [tuple(e) for e in edges]
    present = {frozenset(e) for e in edges}
    done = 0
    m = len(edges)
    for _ in range(max_tries):
        if done >= n_swaps:
            break
        i, j = rng.integers(m, size=2)
        if i == j:
            continue
        a, b = edges[i]
        c, d = edges[j]
        if rng.random() < 0.5:
            c, d = d, c
        if len({a, b, c, d}) < 4 or frozenset((a, d)) in present or frozenset((c, b)) in present:
            continue
        present -= {frozenset((a, b)), frozenset((c, d))}
        present |= {frozenset((a, d)), frozenset((c, b))}
        edges[i], edges[j] = (a, d), (c, b)
        done += 1
    return edges, done


def shuffled_null(g: nx.Graph, seed: int) -> nx.Graph:
    """Degree-preserving randomisation: up to ``10*|E|`` double-edge swaps (``100*|E|``
    attempts), weights permuted onto the new edges, seeded. Achieved swaps are recorded
    in ``graph['provenance']['n_swaps']``."""
    rng = np.random.default_rng(seed)
    orig = list(g.edges)
    m = len(orig)
    edges, done = _double_edge_swaps(orig, 10 * m, 100 * m, rng) if m >= 2 else (orig, 0)
    weights = rng.permutation([w for _, _, w in g.edges(data="weight", default=1.0)])
    h = nx.Graph()
    h.add_nodes_from(g.nodes)
    h.add_weighted_edges_from((u, v, float(w)) for (u, v), w in zip(edges, weights))
    h.graph = {**g.graph, "provenance": {**g.graph["provenance"], "null_of": g.graph["provenance"]["source"],
                                         "null_seed": seed, "n_swaps": done, "n_swaps_target": 10 * m}}
    return h


def nulls(g: nx.Graph, n: int = N_NULLS, base_seed: int = 0) -> list[nx.Graph]:
    return [shuffled_null(g, base_seed + i) for i in range(n)]


def build_prior(name: str, protein_ids: list[str], **kw) -> nx.Graph:
    """Build a registered prior by name (core or contrib)."""
    if name not in PRIORS:
        raise KeyError(f"unknown prior {name!r}; registered: {sorted(PRIORS)}")
    g = PRIORS[name].build(list(protein_ids), **kw)
    validate_prior(g, list(protein_ids))
    return g


register_prior("corum", lambda ids: build_complex_graph(ids, "corum"),
               "CORUM: edge = shared complex, weight = #shared complexes", contrib=False)
register_prior("complexportal", lambda ids: build_complex_graph(ids, "complexportal"),
               "EBI Complex Portal: edge = shared complex, weight = #shared complexes", contrib=False)
register_prior("string", lambda ids, min_score=700: build_string_graph(ids, min_score, "combined"),
               "STRING v12.5 combined score >= 700", contrib=False)
register_prior("string_exp", lambda ids, min_score=700: build_string_graph(ids, min_score, "experimental"),
               "STRING v12.5 experimental channel >= 700", contrib=False)
