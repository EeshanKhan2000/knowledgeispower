"""Contributor-owned edge tests for the S1 variant-to-complex bridge."""

from __future__ import annotations

import json

import jsonschema

import contrib.variant_bridge.variant_bridge as bridge
from contrib.variant_bridge.schema import OUTPUT_SCHEMA


def _validate(out: dict) -> dict:
    jsonschema.validate(out, OUTPUT_SCHEMA)
    return out


def test_invalid_optional_argument_shapes_return_structured_errors():
    cases = [
        bridge.variant_to_complexes("PSMB5", sources=[]),
        bridge.variant_to_complexes("PSMB5", sources=["humap3"]),
        bridge.variant_to_complexes("PSMB5", dataset_proteins="P28074"),
        bridge.variant_to_complexes("PSMB5", dataset_proteins=[42]),
    ]
    for out in cases:
        _validate(out)
        assert out["error"]["code"] == "invalid_input"


def test_duplicate_sources_do_not_duplicate_complexes():
    out = _validate(bridge.variant_to_complexes("PSMB5", sources=["corum", "corum"]))
    keys = [(item["source"], item["complex_id"]) for item in out["complexes"]]
    assert len(keys) == len(set(keys))
    assert all(source == "corum" for source, _ in keys)


def test_transcript_success_has_transcript_resolution_semantics(monkeypatch):
    monkeypatch.setattr(bridge, "_resolve_transcript", lambda transcript: ["PSMB5"])
    out = _validate(bridge.variant_to_complexes("ENST00000361611:c.100A>G"))
    assert out["input_type"] == "hgvs"
    assert out["resolved_gene"] == {"symbol": "PSMB5", "how": "hgvs_transcript"}
    assert out["uniprot"] == ["P28074"]


def test_transcript_upstream_failure_is_structured(monkeypatch):
    def fail(_):
        raise bridge._UpstreamUnavailable("service unavailable")

    monkeypatch.setattr(bridge, "_resolve_transcript", fail)
    out = _validate(bridge.variant_to_complexes("ENST00000361611:c.100A>G"))
    assert out["error"]["code"] == "upstream_unavailable"


def test_transcript_resolution_cache_avoids_second_lookup(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "_CACHE_DIR", tmp_path)
    calls = []

    def resolve(transcript):
        calls.append(transcript)
        return ["PSMB5"]

    monkeypatch.setattr(bridge, "_resolve_ensembl_transcript", resolve)
    assert bridge._resolve_transcript("ENST00000361611") == ["PSMB5"]
    assert bridge._resolve_transcript("ENST00000361611") == ["PSMB5"]
    assert calls == ["ENST00000361611"]
    cache_files = list(tmp_path.glob("*.json"))
    assert len(cache_files) == 1
    assert json.loads(cache_files[0].read_text())["symbols"] == ["PSMB5"]


def test_ensembl_transcript_uses_parent_gene_from_response(monkeypatch):
    requests = []

    def request(url, **_):
        requests.append(url)
        return {"Parent": "ENSG00000100804"}

    monkeypatch.setattr(bridge, "_json_request", request)
    assert bridge._resolve_ensembl_transcript("ENST00000361611.9") == ["PSMB5"]
    assert requests == [
        "https://rest.ensembl.org/lookup/id/ENST00000361611?content-type=application/json"
    ]


def test_refseq_transcript_maps_uniprot_result_back_to_hgnc(monkeypatch):
    responses = iter(
        [
            {"jobId": "job-1"},
            {"results": [{"from": "NM_002797.5", "to": "P28074"}]},
            {"results": [{"from": "NM_002797.5", "to": {"primaryAccession": "P28074"}}]},
        ]
    )
    monkeypatch.setattr(bridge, "_json_request", lambda *_, **__: next(responses))
    assert bridge._resolve_refseq_transcript("NM_002797.5") == ["PSMB5"]


def test_stateful_response_is_cached_but_not_replayed(monkeypatch, tmp_path):
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

    monkeypatch.setattr(bridge, "_CACHE_DIR", tmp_path)
    responses = iter([Response({"jobStatus": "RUNNING"}), Response({"results": []})])
    monkeypatch.setattr(bridge, "urlopen", lambda *_, **__: next(responses))
    url = "https://rest.uniprot.org/idmapping/status/job-1"

    assert bridge._json_request(url, read_cache=False) == {"jobStatus": "RUNNING"}
    assert bridge._json_request(url, read_cache=False) == {"results": []}
    cache_files = list(tmp_path.glob("*.json"))
    assert len(cache_files) == 1
    assert json.loads(cache_files[0].read_text()) == {"results": []}
