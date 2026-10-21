"""S1 variant -> complex bridge. Registers the ``variant_to_complexes`` MCP tool (contrib)."""

from scp_graphfs_mcp.registry import register_tool

from .variant_bridge import IMPLEMENTED, variant_to_complexes
from .schema import INPUT_SCHEMA, OUTPUT_SCHEMA

register_tool(
    "variant_to_complexes",
    variant_to_complexes,
    "Gene symbol, Ensembl gene ID or HGVS-style variant -> gene -> UniProt protein(s) -> "
    "curated complexes (CORUM, Complex Portal) -> partner subunits. Returns [] when the gene "
    "is in no curated complex; returns a structured error for unresolvable input.",
    INPUT_SCHEMA,
    OUTPUT_SCHEMA,
    contrib=True,
)

__all__ = ["IMPLEMENTED", "variant_to_complexes"]
