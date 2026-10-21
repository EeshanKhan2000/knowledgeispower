"""Core MCP tools and contrib mounting rules."""
from scp_graphfs_mcp.server import mounted_tools
from scp_graphfs_mcp.tools import explain_protein, get_complexes
from scp_graphfs_mcp.complexes import complexes_for_accession


def test_contrib_tools_not_mounted_by_default(monkeypatch):
    monkeypatch.delenv("SCP_GRAPHFS_ENABLE_CONTRIB", raising=False)
    names = set(mounted_tools())
    assert {"get_complexes", "explain_protein"} <= names
    assert "variant_to_complexes" not in names


def test_contrib_tool_mounted_when_enabled(monkeypatch):
    monkeypatch.delenv("SCP_GRAPHFS_ENABLE_CONTRIB", raising=False)
    assert "variant_to_complexes" in mounted_tools(["variant_to_complexes"])


def test_get_complexes_matches_snapshot():
    out = get_complexes("P28074")
    assert {c["complex_id"] for c in out["complexes"]} == set(complexes_for_accession("P28074")["complex_id"])
    assert get_complexes("PSMB5")["n_complexes"] == out["n_complexes"]


def test_bad_ids_return_errors_not_exceptions():
    for bad in ["", "NOTAGENE123", "CORUM:999999999", "MB1"]:
        assert "error" in get_complexes(bad)
    assert "error" in explain_protein("NOTAGENE123")
