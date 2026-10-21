"""S1 acceptance tests — variant -> complex bridge.

Written before the implementation. Every expected value is derived at test time
from the snapshots in ``data/raw`` (CORUM, Complex Portal, HGNC) through
``scp_graphfs_mcp.complexes`` / ``scp_graphfs_mcp.ids`` — never hard-coded from
memory. Contributors may ADD tests; never weaken or delete these.

Until ``contrib.variant_bridge.IMPLEMENTED`` is True the behavioural tests are
xfail, so the core CI stays green.
"""

from __future__ import annotations

import socket

import jsonschema
import pytest

from contrib.variant_bridge import IMPLEMENTED, variant_to_complexes
from contrib.variant_bridge.schema import INPUT_SCHEMA, OUTPUT_SCHEMA
from scp_graphfs_mcp.complexes import complexes_for_accession
from scp_graphfs_mcp.ids import hgnc_table, resolve_symbol, uniprot_for_symbol
from scp_graphfs_mcp.registry import TOOLS

impl = pytest.mark.xfail(not IMPLEMENTED, reason="S1 not implemented yet", strict=True)

NO_COMPLEX_CANDIDATES = ["MYH7", "GFAP", "UMOD"]  # verified against snapshots in-test


@pytest.fixture
def offline(monkeypatch):
    """Symbol / Ensembl-gene / gene-bearing HGVS queries must work with no network."""

    def _blocked(*a, **k):
        raise OSError("network disabled in this test")

    monkeypatch.setattr(socket.socket, "connect", _blocked)


def _snapshot_complex_ids(symbol: str) -> set[str]:
    ids = set()
    for acc in uniprot_for_symbol(symbol):
        ids |= set(complexes_for_accession(acc)["complex_id"])
    return ids


def _ok(out: dict) -> dict:
    jsonschema.validate(out, OUTPUT_SCHEMA)
    assert "error" not in out, out.get("error")
    return out


# ----------------------------------------------------------------- registration (runs now)


def test_tool_registered_as_contrib():
    assert "variant_to_complexes" in TOOLS
    entry = TOOLS["variant_to_complexes"]
    assert entry.contrib is True
    jsonschema.Draft202012Validator.check_schema(INPUT_SCHEMA)
    assert entry.input_schema["required"] == ["query"]


# ----------------------------------------------------------------- behaviour (xfail until done)


@impl
def test_proteasome_subunit(offline):
    snap_names = complexes_for_accession(uniprot_for_symbol("PSMB5")[0])["name"].str.lower()
    assert snap_names.str.contains("proteasome").any()  # premise checked against snapshot
    out = _ok(variant_to_complexes("PSMB5"))
    assert out["resolved_gene"] == {"symbol": "PSMB5", "how": "symbol"}
    assert out["uniprot"] == uniprot_for_symbol("PSMB5")
    got = {c["complex_id"] for c in out["complexes"]}
    assert got == _snapshot_complex_ids("PSMB5")
    assert any("proteasome" in c["name"].lower() for c in out["complexes"])


@impl
def test_rna_pol_ii_subunit(offline):
    snap_names = complexes_for_accession(uniprot_for_symbol("POLR2A")[0])["name"].str.lower()
    assert snap_names.str.contains("rna polymerase ii").any()  # premise checked against snapshot
    out = _ok(variant_to_complexes("POLR2A"))
    got = {c["complex_id"] for c in out["complexes"]}
    assert got == _snapshot_complex_ids("POLR2A")
    assert any("rna polymerase ii" in c["name"].lower() for c in out["complexes"])


@impl
@pytest.mark.parametrize("gene", NO_COMPLEX_CANDIDATES)
def test_gene_with_no_curated_complex_returns_empty(gene, offline):
    assert uniprot_for_symbol(gene), f"{gene} has no UniProt mapping in HGNC snapshot"
    assert _snapshot_complex_ids(gene) == set(), f"{gene} is in a complex in this snapshot; pick another"
    out = _ok(variant_to_complexes(gene))
    assert out["complexes"] == []


@impl
def test_previous_symbol_resolves_to_current(offline):
    prev = hgnc_table().set_index("symbol").loc["POLR2A", "prev_symbol"].split("|")[0]
    assert resolve_symbol(prev) == (["POLR2A"], "prev")
    out = _ok(variant_to_complexes(prev))
    assert out["resolved_gene"] == {"symbol": "POLR2A", "how": "prev"}
    assert {c["complex_id"] for c in out["complexes"]} == _snapshot_complex_ids("POLR2A")


@impl
def test_unambiguous_alias_resolves_to_current(offline):
    aliases = hgnc_table().set_index("symbol").loc["POLR2A", "alias_symbol"].split("|")
    unique = [a for a in aliases if resolve_symbol(a) == (["POLR2A"], "alias")]
    assert unique, "snapshot has no unambiguous POLR2A alias"
    out = _ok(variant_to_complexes(unique[0]))
    assert out["resolved_gene"] == {"symbol": "POLR2A", "how": "alias"}


@impl
def test_ambiguous_alias_is_reported_not_guessed(offline):
    # MB1 is an HGNC alias of more than one gene in the snapshot; checked here.
    syms, how = resolve_symbol("MB1")
    assert how == "alias" and len(syms) > 1 and syms == sorted(syms)
    out = variant_to_complexes("MB1")
    jsonschema.validate(out, OUTPUT_SCHEMA)
    assert out["error"]["code"] == "ambiguous_symbol"
    assert sorted(out["error"]["candidates"]) == syms


@impl
def test_ensembl_gene_id(offline):
    ensg = hgnc_table().set_index("symbol").loc["PSMB5", "ensembl_gene_id"]
    out = _ok(variant_to_complexes(ensg))
    assert out["input_type"] == "ensembl_gene"
    assert out["resolved_gene"]["symbol"] == "PSMB5"
    assert {c["complex_id"] for c in out["complexes"]} == _snapshot_complex_ids("PSMB5")


@impl
@pytest.mark.parametrize("hgvs", ["PSMB5:c.100A>G", "NM_002797.5(PSMB5):c.100A>G", "PSMB5:p.Ala20Thr"])
def test_gene_bearing_hgvs(hgvs, offline):
    out = _ok(variant_to_complexes(hgvs))
    assert out["input_type"] == "hgvs"
    assert out["resolved_gene"] == {"symbol": "PSMB5", "how": "hgvs_gene"}
    assert {c["complex_id"] for c in out["complexes"]} == _snapshot_complex_ids("PSMB5")


@impl
@pytest.mark.parametrize("bad", ["", "   ", "NOTAGENE123", "!!!;DROP TABLE", "x" * 10_000, "PSMB5:c.", None, 42])
def test_garbage_returns_structured_error(bad, offline):
    out = variant_to_complexes(bad)  # must not raise
    jsonschema.validate(out, OUTPUT_SCHEMA)
    assert out["error"]["code"] in {"invalid_input", "unresolved_input", "unsupported_variant"}
    assert "complexes" not in out


@impl
def test_partners_and_dataset_flags(offline):
    acc = uniprot_for_symbol("PSMB5")[0]
    snap = complexes_for_accession(acc)
    some_partner = next(m for mem in snap["members"] for m in mem if m != acc)
    all_partners = {m for mem in snap["members"] for m in mem}
    assert "P99999" not in all_partners and "Q00000" not in all_partners  # premise checked against snapshot
    out = _ok(variant_to_complexes("PSMB5", dataset_proteins=[f"{some_partner};Q00000", "P99999"]))
    for c in out["complexes"]:
        row = snap[snap["complex_id"] == c["complex_id"]].iloc[0]
        assert sorted(c["members"]) == sorted(row["members"])
        partner_ids = [p["uniprot"] for p in c["partners"]]
        assert acc not in partner_ids
        assert sorted(partner_ids) == sorted(m for m in row["members"] if m != acc)
        for p in c["partners"]:
            assert p["in_dataset"] == (p["uniprot"] == some_partner)


@impl
def test_source_filter(offline):
    out = _ok(variant_to_complexes("PSMB5", sources=["complexportal"]))
    assert out["complexes"] and all(c["source"] == "complexportal" for c in out["complexes"])
    ids = set(complexes_for_accession(uniprot_for_symbol("PSMB5")[0], ("complexportal",))["complex_id"])
    assert {c["complex_id"] for c in out["complexes"]} == ids
