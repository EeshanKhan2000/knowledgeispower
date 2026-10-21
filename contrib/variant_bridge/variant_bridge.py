"""S1 — variant -> complex bridge (owner: Eeshan Khan). STUB.

Spec: docs/specs/variant_bridge.md. Acceptance tests: tests/test_variant_bridge.py.

Contract summary (the spec is authoritative):

    variant_to_complexes(query, sources=("corum", "complexportal"), dataset_proteins=None) -> dict

* ``query``: gene symbol (current / alias / previous), Ensembl gene ID, or
  HGVS-style variant (``"PSMB5:c.100A>G"``, ``"NM_002797.5(PSMB5):c.100A>G"``,
  ``"ENST...:c.100A>G"``).
* Never raises for bad input: returns ``{"error": {"code", "message", "query"}}``.
* Never invents complexes: a gene in no curated complex returns ``"complexes": []``.
* Reads complexes only from the snapshots via ``scp_graphfs_mcp.complexes``;
  symbol resolution via ``scp_graphfs_mcp.ids`` (HGNC snapshot). Network
  (Ensembl / UniProt REST) only for transcript/RefSeq-only HGVS, results cached
  under ``data/cache/variant_bridge/``.

Set ``IMPLEMENTED = True`` when the implementation is done; the acceptance
tests are xfail until then.
"""

from __future__ import annotations

IMPLEMENTED = False


def variant_to_complexes(query, sources=("corum", "complexportal"), dataset_proteins=None) -> dict:
    raise NotImplementedError("S1 variant_to_complexes: see docs/specs/variant_bridge.md")
