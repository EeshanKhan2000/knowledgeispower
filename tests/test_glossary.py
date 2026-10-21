"""docs/glossary.json schema (S6 contract; also guards the dashboard)."""
import json
from pathlib import Path

import pytest

P = Path(__file__).resolve().parents[1] / "docs" / "glossary.json"
REQUIRED = ["term", "aka", "why", "how", "what", "example", "links"]


@pytest.mark.skipif(not P.exists(), reason="glossary not written yet")
def test_glossary_schema():
    g = json.loads(P.read_text())
    terms = [e["term"] for e in g]
    assert len(terms) == len(set(terms))
    for e in g:
        for k in REQUIRED:
            assert k in e, (e.get("term"), k)
        for link in e["links"]:
            assert link["url"].startswith("https://"), link
        for r in e.get("related", []):
            assert r in terms, (e["term"], r)
    for t in ["protein complex", "stoichiometry", "CORUM", "MNAR", "random walk with restart", "MCP", "HGVS"]:
        assert t in terms
