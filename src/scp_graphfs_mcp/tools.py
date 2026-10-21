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
