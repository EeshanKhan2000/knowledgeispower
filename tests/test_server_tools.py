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


def test_data_tools_roundtrip(tmp_path):
    import anndata as ad
    from scp_graphfs_mcp.datasets import load_petrosius2023
    from scp_graphfs_mcp.tools import build_prior, impute_with_prior, propagate_scores, select_panel

    a = load_petrosius2023()[:, :300].copy()
    p = tmp_path / "x.h5ad"
    a.write_h5ad(p)
    bp = build_prior(list(a.var_names), ["complexportal"])
    h = bp["priors"]["complexportal"]["handle"]
    top = propagate_scores(h, {a.var_names[0]: 1.0})["top"]
    assert top[0]["propagated"] > 0
    rep = impute_with_prior(str(p), "complexportal")
    out = ad.read_h5ad(rep["output_path"])
    assert not np.isnan(np.asarray(out.X)).any()
    assert rep["n_imputed_from_partners"] + rep["n_imputed_by_knn_fallback"] == rep["n_missing"]
    panel = select_panel(str(p), "complexportal", k=5)["panel"]
    assert len(panel) == 5 and all(r["justification"] for r in panel)
    assert "error" in select_panel(str(p), k=0)
    assert "error" in impute_with_prior("/nonexistent.h5ad")
    assert "error" in propagate_scores("nope", {"x": 1})


import numpy as np  # noqa: E402
