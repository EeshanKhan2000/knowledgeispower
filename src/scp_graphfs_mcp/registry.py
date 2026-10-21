"""Plugin registries: the only way contributions enter the core.

Four registries, each with a documented interface and a validator:

=========  =====================================================  ==========================================
Registry   A contributor adds                                     Interface
=========  =====================================================  ==========================================
PRIORS     a graph source                                         ``build(protein_ids) -> networkx.Graph``
                                                                  with ``graph.graph['provenance']``
METHODS    a selection and/or imputation method                   ``impute(adata, graph) -> AnnData`` and/or
                                                                  ``select(adata, graph, k) -> list[str]``
DATASETS   a public SCP dataset loader                            ``load() -> AnnData`` (obs=cells,
                                                                  var=proteins, X=log2+NaN, layers['raw'])
TOOLS      an MCP tool                                            function + JSON input schema; mounted on
                                                                  the server only when enabled
=========  =====================================================  ==========================================

Rules enforced here (contributors cannot opt out):

* every registered prior automatically gets the degree-preserving shuffled
  null (``null_of=<name>``), see :func:`scp_graphfs_mcp.priors.shuffled_null`;
* contrib entries (``contrib=True``) only run in the benchmark with
  ``--include-contrib`` and only write to ``results/contrib/``;
* contrib tools are mounted only when named in ``SCP_GRAPHFS_ENABLE_CONTRIB``
  (comma-separated) or ``--enable-contrib``.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable

import networkx as nx
import numpy as np

PROVENANCE_KEYS = ("source", "version", "url", "sha256")


@dataclass
class PriorEntry:
    name: str
    build: Callable[[list[str]], nx.Graph]
    description: str
    contrib: bool = False


@dataclass
class MethodEntry:
    name: str
    description: str
    impute: Callable | None = None
    select: Callable | None = None
    contrib: bool = False


@dataclass
class DatasetEntry:
    name: str
    load: Callable[[], Any]
    description: str
    contrib: bool = False


@dataclass
class ToolEntry:
    name: str
    func: Callable[..., dict]
    description: str
    input_schema: dict
    output_schema: dict = field(default_factory=dict)
    contrib: bool = False


PRIORS: dict[str, PriorEntry] = {}
METHODS: dict[str, MethodEntry] = {}
DATASETS: dict[str, DatasetEntry] = {}
TOOLS: dict[str, ToolEntry] = {}


def _check_new(reg: dict, name: str) -> None:
    if not name or not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"invalid registry name {name!r}")
    if name in reg:
        raise ValueError(f"{name!r} is already registered")


def register_prior(name: str, build, description: str, *, contrib: bool = True) -> PriorEntry:
    _check_new(PRIORS, name)
    PRIORS[name] = e = PriorEntry(name, build, description, contrib)
    return e


def register_method(name, description, *, impute=None, select=None, contrib: bool = True) -> MethodEntry:
    _check_new(METHODS, name)
    if impute is None and select is None:
        raise ValueError("a method must provide impute and/or select")
    METHODS[name] = e = MethodEntry(name, description, impute, select, contrib)
    return e


def register_dataset(name: str, load, description: str, *, contrib: bool = True) -> DatasetEntry:
    _check_new(DATASETS, name)
    DATASETS[name] = e = DatasetEntry(name, load, description, contrib)
    return e


def register_tool(name, func, description, input_schema, output_schema=None, *, contrib: bool = True) -> ToolEntry:
    _check_new(TOOLS, name)
    validate_tool_schema(input_schema)
    TOOLS[name] = e = ToolEntry(name, func, description, input_schema, output_schema or {}, contrib)
    return e


# --------------------------------------------------------------------------- validators


def validate_prior(graph: nx.Graph, protein_ids: list[str]) -> None:
    """Raise ``ValueError`` unless ``graph`` satisfies the PRIORS interface."""
    if not isinstance(graph, nx.Graph) or graph.is_directed() or graph.is_multigraph():
        raise ValueError("prior must be an undirected simple networkx.Graph")
    extra = set(graph.nodes) - set(protein_ids)
    if extra:
        raise ValueError(f"prior has {len(extra)} nodes not in protein_ids, e.g. {sorted(extra)[:3]}")
    if any(u == v for u, v in graph.edges):
        raise ValueError("prior must not contain self-loops")
    for u, v, w in graph.edges(data="weight", default=1.0):
        if not (np.isfinite(w) and w > 0):
            raise ValueError(f"edge ({u},{v}) has non-positive or non-finite weight {w}")
    prov = graph.graph.get("provenance")
    if not isinstance(prov, dict) or any(k not in prov for k in PROVENANCE_KEYS):
        raise ValueError(f"graph.graph['provenance'] must be a dict with keys {PROVENANCE_KEYS}")


def validate_dataset(adata) -> None:
    """Raise ``ValueError`` unless ``adata`` follows the obs/var/X/layers convention."""
    X = np.asarray(adata.X, dtype=float)
    if X.ndim != 2 or X.shape != (adata.n_obs, adata.n_vars):
        raise ValueError("X must be a dense cells x proteins matrix")
    if np.isinf(X).any():
        raise ValueError("X must not contain inf; use NaN for missing")
    if "raw" not in adata.layers:
        raise ValueError("layers['raw'] (linear intensities) is required")
    raw = np.asarray(adata.layers["raw"], dtype=float)
    obs = ~np.isnan(X)
    if not np.array_equal(obs, ~np.isnan(raw)):
        raise ValueError("X and layers['raw'] must have identical missingness")
    if obs.any() and not np.allclose(np.log2(raw[obs]), X[obs], atol=1e-6):
        raise ValueError("X must equal log2(layers['raw']) on observed entries")
    if not adata.var_names.is_unique or not adata.obs_names.is_unique:
        raise ValueError("obs_names and var_names must be unique")


def validate_tool_schema(schema: dict) -> None:
    if not isinstance(schema, dict) or schema.get("type") != "object" or "properties" not in schema:
        raise ValueError("input_schema must be a JSON-schema object with 'properties'")


# --------------------------------------------------------------------------- discovery


def load_contrib() -> list[str]:
    """Import every ``contrib.<slot>`` package so its ``register_*`` calls run.

    A contrib package that fails to import is skipped and reported, never fatal:
    a broken contribution must not break the core.
    """
    loaded, failed = [], []
    try:
        import contrib
    except ImportError:
        return loaded
    for mod in pkgutil.iter_modules(contrib.__path__):
        try:
            importlib.import_module(f"contrib.{mod.name}")
            loaded.append(mod.name)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{mod.name}: {type(exc).__name__}: {exc}")
    for f in failed:
        print(f"[registry] contrib package skipped: {f}")
    return loaded
