"""S1 — gene or HGVS-style variant to curated protein-complex membership.

The tool deliberately stops at identifier resolution and snapshot-backed
complex membership. It does not predict variant consequence, pathogenicity,
or clinical significance.

Spec: ``docs/specs/variant_bridge.md``.
Acceptance tests: ``tests/test_variant_bridge.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from scp_graphfs_mcp.complexes import SOURCES, complexes_for_accession
from scp_graphfs_mcp.ids import (
    DATA_DIR,
    group_accessions,
    resolve_symbol,
    symbols_for_accession,
    uniprot_for_symbol,
)

IMPLEMENTED = True

_MAX_QUERY_LENGTH = 2048
_HTTP_TIMEOUT_SECONDS = 20
_CACHE_DIR = DATA_DIR / "cache" / "variant_bridge"

_ENSEMBL_GENE_RE = re.compile(r"^ENSG\d+(?:\.\d+)?$", re.IGNORECASE)
_TRANSCRIPT_HGVS_RE = re.compile(
    r"^(?P<transcript>ENST\d+(?:\.\d+)?|NM_\d+(?:\.\d+)?):"
    r"(?P<kind>[cgnmpr])\.(?P<change>\S+)$",
    re.IGNORECASE,
)
_PAREN_GENE_HGVS_RE = re.compile(
    r"^(?P<reference>[A-Z]{2}_[0-9]+(?:\.[0-9]+)?)"
    r"\((?P<gene>[A-Za-z][A-Za-z0-9-]*)\):"
    r"(?P<kind>[cgnmpr])\.(?P<change>\S+)$",
    re.IGNORECASE,
)
_GENE_HGVS_RE = re.compile(
    r"^(?P<gene>[A-Za-z][A-Za-z0-9-]*):"
    r"(?P<kind>[cgnmpr])\.(?P<change>\S+)$",
    re.IGNORECASE,
)
_SYMBOL_LIKE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class _UpstreamUnavailable(RuntimeError):
    """A transcript mapping service could not give a usable response."""


class _TranscriptUnresolved(LookupError):
    """The mapping service responded, but the transcript had no local gene."""


def _error(code: str, message: str, query, *, candidates: list[str] | None = None) -> dict:
    detail = {"code": code, "message": message, "query": query if isinstance(query, str) else None}
    if candidates is not None:
        detail["candidates"] = sorted(set(candidates))
    return {"error": detail}


def _normalise_sources(sources) -> tuple[str, ...] | None:
    if not isinstance(sources, (list, tuple)) or not sources:
        return None
    if not all(isinstance(s, str) and s in SOURCES for s in sources):
        return None
    return tuple(dict.fromkeys(sources))


def _normalise_dataset_proteins(dataset_proteins) -> set[str] | None:
    if dataset_proteins is None:
        return None
    if not isinstance(dataset_proteins, list) or not all(isinstance(p, str) for p in dataset_proteins):
        raise ValueError("dataset_proteins must be an array of protein accessions or protein-group ids")
    return {acc for feature in dataset_proteins for acc in group_accessions(feature)}


def _cache_path(method: str, url: str, body: bytes | None) -> Path:
    key = hashlib.sha256(b"\0".join([method.encode(), url.encode(), body or b""])).hexdigest()
    return _CACHE_DIR / f"{key}.json"


def _write_cache(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _json_request(
    url: str,
    *,
    data: dict[str, str] | None = None,
    read_cache: bool = True,
    timeout: int = _HTTP_TIMEOUT_SECONDS,
):
    """Return validated JSON from cache or a standard-library HTTP request.

    Every successful upstream response is cached. ``read_cache=False`` is for
    stateful UniProt job endpoints whose old response must not be replayed.
    """
    method = "POST" if data is not None else "GET"
    body = urlencode(data).encode("ascii") if data is not None else None
    path = _cache_path(method, url, body)
    if read_cache and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            # A corrupt cache is not evidence. Fetch a fresh response instead.
            pass

    headers = {"Accept": "application/json", "User-Agent": "scp-graphfs-mcp/0.1 variant-bridge"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS endpoints only
            raw = response.read()
    except HTTPError as exc:
        if exc.code == 404:
            raise _TranscriptUnresolved(f"transcript lookup returned HTTP 404 for {url}") from exc
        raise _UpstreamUnavailable(f"transcript lookup returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise _UpstreamUnavailable(f"transcript lookup failed: {exc}") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise _UpstreamUnavailable("transcript lookup did not return valid JSON") from exc
    try:
        _write_cache(path, payload)
    except OSError:
        # A read-only cache must not turn a valid mapping into a failure.
        pass
    return payload


def _resolve_ensembl_transcript(transcript: str) -> list[str]:
    stable_id = transcript.upper().split(".", 1)[0]
    url = (
        f"https://rest.ensembl.org/lookup/id/{quote(stable_id, safe='')}"
        "?content-type=application/json"
    )
    payload = _json_request(url)
    if not isinstance(payload, dict) or not isinstance(payload.get("Parent"), str):
        raise _TranscriptUnresolved(f"Ensembl returned no parent gene for {transcript}")
    symbols, _ = resolve_symbol(payload["Parent"])
    if not symbols:
        raise _TranscriptUnresolved(f"the parent gene for {transcript} is absent from the HGNC snapshot")
    return symbols


def _resolve_refseq_transcript(transcript: str) -> list[str]:
    """Map a RefSeq nucleotide transcript through UniProt's documented ID service."""
    accession = transcript.upper()
    run = _json_request(
        "https://rest.uniprot.org/idmapping/run",
        data={"from": "RefSeq_Nucleotide", "to": "UniProtKB", "ids": accession},
        read_cache=False,
    )
    if not isinstance(run, dict) or not isinstance(run.get("jobId"), str):
        raise _UpstreamUnavailable("UniProt ID mapping did not return a job id")

    job_id = run["jobId"]
    deadline = time.monotonic() + _HTTP_TIMEOUT_SECONDS
    while True:
        status = _json_request(
            f"https://rest.uniprot.org/idmapping/status/{quote(job_id, safe='')}", read_cache=False
        )
        if isinstance(status, dict) and status.get("jobStatus") in {"RUNNING", "NEW"}:
            if time.monotonic() >= deadline:
                raise _UpstreamUnavailable("UniProt ID mapping timed out")
            time.sleep(0.25)
            continue
        if isinstance(status, dict) and status.get("jobStatus") == "ERROR":
            raise _TranscriptUnresolved(f"UniProt could not resolve {transcript}")
        break

    results = _json_request(
        f"https://rest.uniprot.org/idmapping/results/{quote(job_id, safe='')}?format=json"
    )
    rows = results.get("results", []) if isinstance(results, dict) else []
    accessions: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        target = row.get("to")
        if isinstance(target, str):
            accessions.add(target)
        elif isinstance(target, dict) and isinstance(target.get("primaryAccession"), str):
            accessions.add(target["primaryAccession"])
    symbols = sorted({symbol for acc in accessions for symbol in symbols_for_accession(acc)})
    if not symbols:
        raise _TranscriptUnresolved(f"UniProt returned no HGNC-backed mapping for {transcript}")
    return symbols


def _resolve_transcript(transcript: str) -> list[str]:
    normalised = transcript.upper()
    path = _cache_path("RESOLVE", f"transcript:{normalised}", None)
    if path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            symbols = cached.get("symbols") if isinstance(cached, dict) else None
            if isinstance(symbols, list) and symbols and all(isinstance(s, str) for s in symbols):
                return sorted(set(symbols))
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass

    symbols = (
        _resolve_ensembl_transcript(normalised)
        if normalised.startswith("ENST")
        else _resolve_refseq_transcript(normalised)
    )
    try:
        _write_cache(path, {"transcript": normalised, "symbols": sorted(set(symbols))})
    except OSError:
        pass
    return symbols


def _resolve_query(query: str) -> tuple[str, str, list[str]] | dict:
    """Return ``(input_type, how, symbols)`` or a structured error."""
    parenthesised = _PAREN_GENE_HGVS_RE.fullmatch(query)
    if parenthesised:
        symbols, _ = resolve_symbol(parenthesised.group("gene"))
        if not symbols:
            return _error("unresolved_input", "the HGVS gene is not in the HGNC snapshot", query)
        if len(symbols) > 1:
            return _error("ambiguous_symbol", "the HGVS gene resolves to multiple genes", query,
                          candidates=symbols)
        return "hgvs", "hgvs_gene", symbols

    transcript = _TRANSCRIPT_HGVS_RE.fullmatch(query)
    if transcript:
        try:
            symbols = _resolve_transcript(transcript.group("transcript"))
        except _TranscriptUnresolved as exc:
            return _error("unresolved_input", str(exc), query)
        except _UpstreamUnavailable as exc:
            return _error("upstream_unavailable", str(exc), query)
        if not symbols:
            return _error("unresolved_input", "the transcript has no HGNC-backed gene mapping", query)
        if len(symbols) > 1:
            return _error("ambiguous_symbol", "the transcript maps to multiple HGNC genes", query,
                          candidates=symbols)
        return "hgvs", "hgvs_transcript", symbols

    gene_hgvs = _GENE_HGVS_RE.fullmatch(query)
    if gene_hgvs:
        symbols, _ = resolve_symbol(gene_hgvs.group("gene"))
        if not symbols:
            return _error("unresolved_input", "the HGVS gene is not in the HGNC snapshot", query)
        if len(symbols) > 1:
            return _error("ambiguous_symbol", "the HGVS gene resolves to multiple genes", query,
                          candidates=symbols)
        return "hgvs", "hgvs_gene", symbols

    if ":" in query:
        return _error("unsupported_variant", "unsupported or malformed HGVS-style variant", query)
    if not _SYMBOL_LIKE_RE.fullmatch(query):
        return _error("invalid_input", "query is not a supported gene, Ensembl, or HGVS identifier", query)

    symbols, how = resolve_symbol(query)
    if not symbols:
        return _error("unresolved_input", "query is not present in the HGNC snapshot", query)
    if len(symbols) > 1:
        return _error("ambiguous_symbol", "query resolves to multiple HGNC genes", query,
                      candidates=symbols)
    input_type = "ensembl_gene" if _ENSEMBL_GENE_RE.fullmatch(query) else "gene_symbol"
    return input_type, how, symbols


def _complex_records(accessions: list[str], sources: tuple[str, ...], dataset: set[str] | None) -> list[dict]:
    rows: dict[tuple[str, str], object] = {}
    for accession in accessions:
        for row in complexes_for_accession(accession, sources).itertuples():
            rows.setdefault((row.source, row.complex_id), row)

    query_accessions = set(accessions)
    complexes = []
    for key in sorted(rows):
        row = rows[key]
        members = sorted(set(row.members))
        partners = [
            {
                "uniprot": member,
                "symbols": symbols_for_accession(member),
                "in_dataset": None if dataset is None else member in dataset,
            }
            for member in members
            if member not in query_accessions
        ]
        complexes.append(
            {
                "complex_id": row.complex_id,
                "source": row.source,
                "name": row.name,
                "members": members,
                "partners": partners,
            }
        )
    return complexes


def variant_to_complexes(query, sources=("corum", "complexportal"), dataset_proteins=None) -> dict:
    """Resolve a gene or HGVS-style variant to exact complex records and partners.

    Bad user input returns a structured error and never raises. Local snapshot
    or programming failures remain visible to the MCP server's exception guard.
    """
    if not isinstance(query, str):
        return _error("invalid_input", "query must be a string", query)
    query = query.strip()
    if not query:
        return _error("invalid_input", "query must not be blank", query)
    if len(query) > _MAX_QUERY_LENGTH:
        return _error("invalid_input", f"query exceeds {_MAX_QUERY_LENGTH} characters", query)

    selected_sources = _normalise_sources(sources)
    if selected_sources is None:
        return _error("invalid_input", f"sources must be a non-empty subset of {list(SOURCES)}", query)
    try:
        dataset = _normalise_dataset_proteins(dataset_proteins)
    except ValueError as exc:
        return _error("invalid_input", str(exc), query)

    resolved = _resolve_query(query)
    if isinstance(resolved, dict):
        return resolved
    input_type, how, symbols = resolved
    symbol = symbols[0]
    accessions = uniprot_for_symbol(symbol)
    warnings = []
    if not accessions:
        warnings.append(f"HGNC has no UniProt accession for {symbol} in the committed snapshot.")

    return {
        "query": query,
        "input_type": input_type,
        "resolved_gene": {"symbol": symbol, "how": how},
        "uniprot": accessions,
        "complexes": _complex_records(accessions, selected_sources, dataset),
        "warnings": warnings,
    }
