"""Shared helpers for the knowledge-source representation modules (reactome, biogrid, intact, monarch,
cocitation). Not a representation itself.

Derived caches are compact accession-level files written next to the raw download in
``data/cache/reps/<name>/``. Each carries a small JSON sidecar recording the raw files' SHA-256, size
and mtime; the cache is rebuilt automatically when a raw file's size or mtime changes.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import networkx as nx
import numpy as np

from ..features import _accs
from ..ids import DATA_DIR, extract_accessions, hgnc_table

REPS_DIR = DATA_DIR / "cache" / "reps"
USER_AGENT = "scp-graphfs-mcp/0.1 (research)"


def source_dir(name: str) -> Path:
    return REPS_DIR / name


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _stamp(paths: list[Path]) -> dict:
    return {p.name: {"size": p.stat().st_size, "mtime": int(p.stat().st_mtime)} for p in paths}


def cache_fresh(meta_path: Path, raws: list[Path]) -> bool:
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text())
    except (OSError, ValueError):
        return False
    st = _stamp(raws)
    return all(meta.get("raw", {}).get(k, {}).get(f) == v[f] for k, v in st.items() for f in ("size", "mtime"))


def write_meta(meta_path: Path, raws: list[Path], **extra) -> dict:
    st = _stamp(raws)
    for p in raws:
        st[p.name]["sha256"] = file_sha256(p)
    meta = {"raw": st, **extra}
    meta_path.write_text(json.dumps(meta, indent=1, sort_keys=True))
    return meta


def read_meta(meta_path: Path) -> dict:
    return json.loads(meta_path.read_text())


def save_edges(path: Path, edges: dict[tuple[str, str], float]) -> None:
    """Write an undirected accession-level edge list ``{(a, b): w}`` (a < b) as a compact .npz."""
    nodes = sorted({a for e in edges for a in e})
    pos = {a: k for k, a in enumerate(nodes)}
    i = np.fromiter((pos[a] for a, _ in edges), np.int32, len(edges))
    j = np.fromiter((pos[b] for _, b in edges), np.int32, len(edges))
    w = np.fromiter(edges.values(), np.float64, len(edges))
    np.savez_compressed(path, nodes=np.array(nodes, dtype="U12"), i=i, j=j, w=w)


def load_edges(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    z = np.load(path, allow_pickle=False)
    return z["nodes"], z["i"], z["j"], z["w"]


def graph_from_edges(var_names, nodes: np.ndarray, i: np.ndarray, j: np.ndarray, w: np.ndarray,
                     provenance: dict | None = None) -> nx.Graph:
    """Graph over the var_names strings (all added as nodes); an edge joins two var_names whose
    first accessions are linked in the accession-level edge list."""
    names = list(var_names)
    g = nx.Graph()
    g.add_nodes_from(names)
    by_acc: dict[str, list[str]] = {}
    for n, a in zip(names, _accs(names)):
        if a:
            by_acc.setdefault(a, []).append(n)
    node_pos = {a: k for k, a in enumerate(nodes.tolist())}
    present = np.zeros(len(nodes), bool)
    idx = [node_pos[a] for a in by_acc if a in node_pos]
    present[idx] = True
    m = present[i] & present[j]
    for a, b, x in zip(nodes[i[m]].tolist(), nodes[j[m]].tolist(), w[m].tolist()):
        for u in by_acc[a]:
            for v in by_acc[b]:
                if u != v:
                    g.add_edge(u, v, weight=float(x))
    if provenance:
        g.graph["provenance"] = provenance
    return g


@lru_cache(maxsize=1)
def entrez_to_uniprot() -> dict[str, tuple[str, ...]]:
    """HGNC (approved genes): NCBI Gene ID -> canonical UniProt accessions."""
    out: dict[str, tuple[str, ...]] = {}
    for eid, up in zip(hgnc_table()["entrez_id"], hgnc_table()["uniprot_ids"]):
        accs = tuple(extract_accessions(up.replace("|", " ")))
        if eid and accs:
            out[str(eid).split(".")[0]] = accs
    return out


@lru_cache(maxsize=1)
def hgnc_to_uniprot() -> dict[str, tuple[str, ...]]:
    """HGNC (approved genes): ``'HGNC:5'`` -> canonical UniProt accessions."""
    out: dict[str, tuple[str, ...]] = {}
    for hid, up in zip(hgnc_table()["hgnc_id"], hgnc_table()["uniprot_ids"]):
        accs = tuple(extract_accessions(up.replace("|", " ")))
        if hid and accs:
            out[hid] = accs
    return out
