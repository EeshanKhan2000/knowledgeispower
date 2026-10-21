# S1 — Variant → complex bridge (`variant_to_complexes`)

**Owner:** Eeshan Khan (@EeshanKhan2000) · **Branch:** `contrib/eeshan-s1` · **Checkpoint:** Oct 21, 14:00 ET
**Status:** optional, off the critical path. The core demo and benchmark work without it.

## Purpose
Answer "if this gene (or this variant) is hit, which protein machines does it affect, and which
partner subunits would show it?" The chain:

```
gene symbol | Ensembl gene ID | HGVS-style variant
   → current HGNC gene symbol
   → UniProt accession(s)
   → curated complexes (CORUM, EBI Complex Portal)
   → partner subunits (+ whether each is measured in our dataset)
```

## Tool
- **Name:** `variant_to_complexes`
- **Python:** `contrib/variant_bridge/variant_bridge.py::variant_to_complexes(query, sources=("corum","complexportal"), dataset_proteins=None) -> dict`
- **Registered by:** `contrib/variant_bridge/__init__.py` through `registry.register_tool(..., contrib=True)`.
  The registration already exists. Do not change it, except to fix a bug.
- **Mounted on the MCP server only with** `scp-graphfs-mcp --enable-contrib variant_to_complexes`.

## Exact schemas
The schemas live in `contrib/variant_bridge/schema.py` (`INPUT_SCHEMA`, `OUTPUT_SCHEMA`) and are
authoritative. Changing them needs Amit's approval. In summary:

Input:
```json
{"query": "PSMB5:c.100A>G", "sources": ["corum", "complexportal"], "dataset_proteins": ["P28074", "P20618;Q5JRX3"]}
```

Success output:
```json
{
  "query": "PSMB5:c.100A>G",
  "input_type": "hgvs",
  "resolved_gene": {"symbol": "PSMB5", "how": "hgvs_gene"},
  "uniprot": ["P28074"],
  "complexes": [
    {"complex_id": "CORUM:...", "source": "corum", "name": "...", "members": ["P28074", "..."],
     "partners": [{"uniprot": "...", "symbols": ["..."], "in_dataset": true}]}
  ],
  "warnings": []
}
```
- `how` ∈ `symbol | prev | alias | ensembl | hgvs_gene | hgvs_transcript`.
- `partners` = `members` minus the query protein(s). `in_dataset` is `null` when `dataset_proteins` isn't given.
- A gene in no curated complex returns `"complexes": []`. **Never invent a complex.**

Error output (returned, never raised):
```json
{"error": {"code": "ambiguous_symbol", "message": "...", "query": "MB1", "candidates": ["CD79A", "PSMB5"]}}
```
`code` ∈ `invalid_input | unresolved_input | ambiguous_symbol | unsupported_variant | upstream_unavailable`.

## Data sources: what you may read
- **Complexes:** only via `scp_graphfs_mcp.complexes` (`complexes_for_accession`, `load_complexes`),
  which reads the CORUM and Complex Portal snapshots in `data/raw/`.
- **Symbols / aliases / previous symbols / Ensembl gene → symbol → UniProt:** via `scp_graphfs_mcp.ids`
  (`resolve_symbol`, `uniprot_for_symbol`, `symbols_for_accession`), which reads the HGNC snapshot.
  These queries **must work offline**, and the tests enforce it.
- **Transcript- or RefSeq-only HGVS** (`ENST00000...:c.…`, `NM_...:c.…` with no gene in parentheses):
  you may call a documented API:
  - Ensembl REST `GET /lookup/id/{ENST}` → `Parent` gene (https://rest.ensembl.org/documentation/info/lookup);
  - or Ensembl `variant_recoder` (https://rest.ensembl.org/documentation/info/variant_recoder_post);
  - or UniProt ID mapping (https://rest.uniprot.org/idmapping).

  Cache every response in `data/cache/variant_bridge/` (gitignored), keyed by the request. If the API
  is unreachable, return `upstream_unavailable`. No new dependencies: use `urllib` from the standard
  library.
- Nothing is resolved by guessing, fuzzy matching, or an LLM.

## Off-limits (enforced by CODEOWNERS and review)
You may **not** modify `src/scp_graphfs_mcp/priors.py`, anything in `benchmarks/` or `results/`,
`registry.py`, or any existing tool's schema. You write in `contrib/variant_bridge/`,
`tests/contrib/` (extra tests) and your own docs only. `tests/test_variant_bridge.py` is the
acceptance contract. You may **add** tests but never weaken or delete them.

## Acceptance tests (`tests/test_variant_bridge.py`)
Every expected value is computed at test time from the snapshots. They are `xfail` until you set
`IMPLEMENTED = True`. They cover:

1. PSMB5 → exactly the snapshot's complexes for P28074, including a proteasome complex.
2. POLR2A → exactly the snapshot's complexes, including RNA polymerase II.
3. MYH7 / GFAP / UMOD (each verified in-test to have zero complexes) → `[]`.
4. Previous symbol (`POLR2`, read from HGNC) → POLR2A, `how="prev"`.
5. Unambiguous alias (read from HGNC) → POLR2A, `how="alias"`.
6. Ambiguous alias `MB1` (an alias of two genes in HGNC) → `ambiguous_symbol` with both candidates.
7. Ensembl gene ID → PSMB5.
8. Gene-bearing HGVS: `PSMB5:c.100A>G`, `NM_002797.5(PSMB5):c.100A>G`, `PSMB5:p.Ala20Thr`.
9. Garbage (`""`, whitespace, unknown symbol, injection-like strings, 10 kB strings, `PSMB5:c.`,
   `None`, `42`) → a structured error, never an exception.
10. `partners` and `in_dataset` flags are exact.
11. The `sources` filter works.

All except 1–3 and 7–8 also validate against `OUTPUT_SCHEMA`; those do too.

## Merge gate
1. `pytest` passes with `IMPLEMENTED = True` (CI green).
2. A **real** agent transcript in `contrib/variant_bridge/TRANSCRIPT.md`: Claude (Desktop or Code)
   connected to `scp-graphfs-mcp --enable-contrib variant_to_complexes`, answering
   *"A patient has PSMB5:c.100A>G. Which protein machines are affected, and which of their partner
   subunits are measured in data/datasets/petrosius2023_aml_sc.h5ad?"* See `docs/ONBOARDING.md` for
   the client config.
3. A 3-sentence PR description (what, why) plus an AI-assistance disclosure.
4. Amit merges. **If the checkpoint is missed or tests fail, the branch stays unmerged and the tool
   leaves the demo.** No hard feelings.
