"""Core MCP tools. Each is a plain function returning a JSON-serialisable dict, registered in
:data:`scp_graphfs_mcp.registry.TOOLS` with ``contrib=False``. Bad input returns
``{"error": {...}}`` rather than raising.
"""

from __future__ import annotations

from .complexes import SOURCES, complexes_for_accession, load_complexes
from .ids import canonical_accession, resolve_symbol, symbols_for_accession, uniprot_for_symbol
from .registry import register_tool


def _err(code: str, message: str, **kw) -> dict:
    return {"error": {"code": code, "message": message, **kw}}


def _to_accessions(identifier: str) -> tuple[list[str], dict]:
    """UniProt accession or gene symbol/alias -> canonical accessions + how it resolved."""
    if not isinstance(identifier, str) or not identifier.strip():
        return [], {"how": "invalid"}
    acc = canonical_accession(identifier)
    if acc:
        return [acc], {"how": "uniprot"}
    syms, how = resolve_symbol(identifier)
    if len(syms) > 1:
        return [], {"how": "ambiguous", "candidates": syms}
    if not syms:
        return [], {"how": "unresolved"}
    return uniprot_for_symbol(syms[0]), {"how": how, "symbol": syms[0]}


def get_complexes(id: str, sources: list[str] | None = None) -> dict:
    """Complexes containing a protein (UniProt accession or gene symbol), or one complex by id."""
    sources = tuple(sources or SOURCES)
    if isinstance(id, str) and (id.startswith("CORUM:") or id.startswith("CPX-")):
        df = load_complexes(sources)
        rows = df[df["complex_id"] == id]
        if rows.empty:
            return _err("not_found", f"no complex {id} in {list(sources)}")
        query = {"complex_id": id}
    else:
        accs, how = _to_accessions(id)
        if not accs:
            return _err(f"{how['how']}_identifier", f"could not resolve {id!r} to a UniProt accession", **how)
        import pandas as pd

        rows = pd.concat([complexes_for_accession(a, sources) for a in accs])
        query = {"input": id, "uniprot": accs, **how}
    return {
        "query": query,
        "n_complexes": int(len(rows)),
        "complexes": [
            {
                "complex_id": r.complex_id,
                "source": r.source,
                "name": r.name,
                "subunits": [{"uniprot": m, "symbols": symbols_for_accession(m)} for m in r.members],
            }
            for r in rows.itertuples()
        ],
        "provenance": "data/PROVENANCE.md (CORUM + EBI Complex Portal snapshots)",
    }


def explain_protein(id: str) -> dict:
    """Plain-language card: what the protein is called, which curated complexes it is in."""
    accs, how = _to_accessions(id)
    if not accs:
        return _err(f"{how['how']}_identifier", f"could not resolve {id!r}", **how)
    import pandas as pd

    rows = pd.concat([complexes_for_accession(a) for a in accs])
    partners = sorted({m for mem in rows["members"] for m in mem} - set(accs))
    symbols = sorted({s for a in accs for s in symbols_for_accession(a)})
    names = rows["name"].tolist()
    if names:
        summary = (
            f"{'/'.join(symbols) or accs[0]} is a subunit of {len(names)} curated complex"
            f"{'es' if len(names) != 1 else ''} (e.g. {'; '.join(names[:3])}), "
            f"shared with {len(partners)} distinct partner proteins. Because complex subunits are "
            "made in fixed ratios and unassembled subunits tend to be degraded, its abundance is "
            "expected to co-vary with these partners."
        )
    else:
        summary = (
            f"{'/'.join(symbols) or accs[0]} is in no curated complex in the CORUM or Complex Portal "
            "snapshots, so the complex prior gives no information about it (imputation falls back to kNN)."
        )
    return {
        "input": id,
        "uniprot": accs,
        "symbols": symbols,
        "resolved_how": how["how"],
        "n_complexes": int(len(rows)),
        "complexes": [{"complex_id": r.complex_id, "source": r.source, "name": r.name} for r in rows.itertuples()],
        "complex_graph_degree": len(partners),
        "summary": summary,
    }


_ID = {"type": "string", "description": "UniProt accession (e.g. P28074) or gene symbol (e.g. PSMB5)."}
_SOURCES = {"type": "array", "items": {"type": "string", "enum": list(SOURCES)}}

register_tool(
    "get_complexes",
    get_complexes,
    "Curated complexes (CORUM + EBI Complex Portal) containing a protein, with all subunits and "
    "source ids. Also accepts a complex id (CORUM:123 or CPX-123).",
    {"type": "object", "properties": {"id": _ID, "sources": _SOURCES}, "required": ["id"]},
    contrib=False,
)
register_tool(
    "explain_protein",
    explain_protein,
    "Plain-language card for one protein: names, curated complexes, and degree in the complex graph.",
    {"type": "object", "properties": {"id": _ID}, "required": ["id"]},
    contrib=False,
)


# --------------------------------------------------------------------------- graph / data tools

import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

import anndata as ad  # noqa: E402
import numpy as np  # noqa: E402

_HANDLES: dict[str, object] = {}
_PRIOR_NAMES = ["corum", "complexportal", "string", "string_exp"]


def _graph_for(prior: str, protein_ids: list[str]):
    from .priors import build_prior

    if prior in _HANDLES:
        return _HANDLES[prior]
    return build_prior(prior, protein_ids)


def build_prior(proteins: list[str], sources: list[str] | None = None, string_min_score: int = 700) -> dict:
    """Build prior graph(s) over a protein list; returns coverage + a handle per source."""
    from .priors import build_prior as _build

    if not isinstance(proteins, list) or not proteins or not all(isinstance(p, str) for p in proteins):
        return _err("invalid_input", "proteins must be a non-empty list of UniProt accessions / protein-group ids")
    sources = sources or ["corum", "complexportal"]
    out = {}
    for s in sources:
        if s not in _PRIOR_NAMES:
            return _err("invalid_input", f"unknown source {s!r}; choose from {_PRIOR_NAMES}")
        kw = {"min_score": string_min_score} if s.startswith("string") else {}
        try:
            g = _build(s, list(dict.fromkeys(proteins)), **kw)
        except ValueError as exc:
            return _err("invalid_input", str(exc))
        h = f"prior-{s}-{uuid.uuid4().hex[:8]}"
        _HANDLES[h] = g
        cov = g.graph["coverage"]
        degs = sorted(g.degree, key=lambda x: -x[1])[:5]
        out[s] = {"handle": h, "n_proteins": cov["n_features"], "n_edges": cov["n_edges"],
                  "n_proteins_with_partners": cov["n_with_edges"], "unmapped": cov["unmapped"][:50],
                  "unmapped_fraction": cov["unmapped_fraction"],
                  "top_degree": [{"protein": p, "symbols": symbols_for_accession(p.split(';')[0]), "degree": d}
                                 for p, d in degs],
                  "provenance": {k: v for k, v in g.graph["provenance"].items()}}
    return {"priors": out, "note": "Use a handle in propagate_scores; a shuffled null of each graph is available "
                                   "in the benchmark (results/), not here."}


def propagate_scores(handle: str, scores: dict, alpha: float = 0.5, top: int = 20) -> dict:
    """Random walk with restart of non-negative scores over a prior graph (alpha = restart probability)."""
    from .methods import propagate

    g = _HANDLES.get(handle)
    if g is None:
        return _err("unknown_handle", f"{handle!r}; call build_prior first")
    if not isinstance(scores, dict) or not scores:
        return _err("invalid_input", "scores must be a non-empty {protein: score} object")
    try:
        p = propagate(g, scores, list(g.nodes), alpha=float(alpha))
    except ValueError as exc:
        return _err("invalid_input", str(exc))
    names = list(g.nodes)
    order = np.argsort(-p)[: int(top)]
    return {"alpha": alpha, "top": [{"protein": names[i], "symbols": symbols_for_accession(names[i].split(';')[0]),
                                     "propagated": float(p[i]), "seed_score": float(scores.get(names[i], 0.0))}
                                    for i in order]}


def _read(h5ad_path: str):
    p = Path(h5ad_path).expanduser()
    if p.suffix != ".h5ad" or not p.is_file():
        return None, _err("invalid_input", f"not an existing .h5ad file: {h5ad_path}")
    a = ad.read_h5ad(p)
    if "raw" not in a.layers:
        a.layers["raw"] = np.exp2(np.asarray(a.X, float))
    return a, None


def impute_with_prior(h5ad_path: str, prior: str = "complexportal", output_path: str | None = None) -> dict:
    """Impute NaNs from observed co-complex partners in the same cell (kNN fallback); writes a new .h5ad."""
    from .methods import impute_with_prior as _impute

    a, err = _read(h5ad_path)
    if err:
        return err
    g = _graph_for(prior, list(a.var_names))
    res = _impute(a, g)
    out_path = Path(output_path) if output_path else Path(h5ad_path).with_name(Path(h5ad_path).stem + f".imputed_{prior}.h5ad")
    if out_path.suffix != ".h5ad":
        return _err("invalid_input", "output_path must end in .h5ad")
    res.uns["impute_with_prior"]["prior"] = {k: str(v) for k, v in res.uns["impute_with_prior"]["prior"].items()}
    res.write_h5ad(out_path)
    rep = res.uns["impute_with_prior"]
    by_prior = np.asarray(res.layers["imputed_by_prior"])
    per_prot = by_prior.sum(0)
    top = np.argsort(-per_prot)[:10]
    return {"output_path": str(out_path), "prior": prior, "beta": rep["beta"],
            "n_missing": rep["n_missing"], "n_imputed_from_partners": rep["n_imputed_by_prior"],
            "n_imputed_by_knn_fallback": rep["n_imputed_by_knn_fallback"],
            "proteins_most_inferred_from_partners": [
                {"protein": a.var_names[i], "symbols": symbols_for_accession(a.var_names[i].split(';')[0]),
                 "n_cells_filled_from_partners": int(per_prot[i])} for i in top if per_prot[i] > 0],
            "caveat": "In the benchmark (results/imputation.json) check whether this prior beat kNN and its shuffled null "
                      "before trusting partner-based values."}


def select_panel(h5ad_path: str, prior: str = "complexportal", k: int = 25, mode: str = "soft_weight") -> dict:
    """Choose k proteins (detected in >=80% of cells) that best summarise the rest; each with a justification."""
    from .methods import select_features

    a, err = _read(h5ad_path)
    if err:
        return err
    if not isinstance(k, int) or not 1 <= k <= a.n_vars:
        return _err("invalid_input", f"k must be an integer in [1, {a.n_vars}]")
    g = _graph_for(prior, list(a.var_names)) if mode != "none" else None
    try:
        panel, score = select_features(a, g, k, mode, return_scores=True)
    except (ValueError, NotImplementedError) as exc:
        return _err("invalid_input", str(exc))
    names = list(a.var_names)
    rows = []
    for rank, p in enumerate(panel, 1):
        acc = p.split(";")[0]
        cx = complexes_for_accession(acc)
        partners = sorted(set(g.neighbors(p))) if g is not None and p in g else []
        psym = [s for q in partners[:6] for s in symbols_for_accession(q.split(';')[0])[:1]]
        sym = "/".join(symbols_for_accession(acc)) or acc
        if len(cx):
            why = f"{sym} is in {cx['name'].iloc[0]}" + (f" with {', '.join(psym)}" if psym else "") + \
                  f" ({len(cx)} curated complexes, {len(partners)} partners measured here)."
        else:
            why = f"{sym}: high variance across cells; no curated complex, so it carries information the prior cannot."
        rows.append({"rank": rank, "protein": p, "symbols": symbols_for_accession(acc),
                     "score": float(score[names.index(p)]) if score is not None else None, "justification": why})
    return {"mode": mode, "prior": prior if g is not None else None, "k": k, "panel": rows}


_H5 = {"type": "string", "description": "Path to a .h5ad (cells=obs, proteins=var, X=log2 with NaN missing)."}
_PRIOR = {"type": "string", "enum": _PRIOR_NAMES, "default": "complexportal"}
register_tool("build_prior", build_prior,
              "Build curated-complex (and/or STRING) prior graphs over a protein list: coverage, unmapped ids, "
              "hub proteins, and a handle for propagate_scores.",
              {"type": "object", "properties": {
                  "proteins": {"type": "array", "items": {"type": "string"}},
                  "sources": {"type": "array", "items": {"type": "string", "enum": _PRIOR_NAMES}},
                  "string_min_score": {"type": "integer", "minimum": 400, "maximum": 1000, "default": 700}},
               "required": ["proteins"]}, contrib=False)
register_tool("propagate_scores", propagate_scores,
              "Random walk with restart of {protein: score} over a prior graph handle.",
              {"type": "object", "properties": {
                  "handle": {"type": "string"}, "scores": {"type": "object", "additionalProperties": {"type": "number"}},
                  "alpha": {"type": "number", "minimum": 0.01, "maximum": 1, "default": 0.5},
                  "top": {"type": "integer", "default": 20}},
               "required": ["handle", "scores"]}, contrib=False)
register_tool("impute_with_prior", impute_with_prior,
              "Fill missing values in a single-cell proteomics .h5ad from observed co-complex partners in the same "
              "cell (kNN fallback). Writes a new .h5ad; reports how many values came from partners.",
              {"type": "object", "properties": {"h5ad_path": _H5, "prior": _PRIOR,
                                                "output_path": {"type": "string"}},
               "required": ["h5ad_path"]}, contrib=False)
register_tool("select_panel", select_panel,
              "Choose a k-protein measurement panel (prior-weighted or plain HVP) with a per-protein justification.",
              {"type": "object", "properties": {"h5ad_path": _H5, "prior": _PRIOR,
                                                "k": {"type": "integer", "minimum": 1, "default": 25},
                                                "mode": {"type": "string", "enum": ["soft_weight", "none", "hard_filter"],
                                                         "default": "soft_weight"}},
               "required": ["h5ad_path"]}, contrib=False)
