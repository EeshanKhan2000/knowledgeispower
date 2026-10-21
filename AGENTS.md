# AGENTS.md: instructions for coding agents

Read this whole file before editing anything. It's short on purpose.

**Breadcrumbs:** before starting work, read the latest comments on GitHub issue #1 ("Updates log"):
https://github.com/xX-its-amit-Xx/knowledgeispower/issues/1. Phase-2 ideas are the issues labelled
`phase2`. After you push something others depend on, add a short comment to #1.

## Mission
Claim under test: *Curated protein-complex membership (CORUM, EBI Complex Portal) is a better prior for reconstructing a cell's protein state from incomplete single-cell proteomics measurements than data alone, than generic PPI networks (STRING), and than a degree-preserving shuffled version of the same graph.*
Primary task: impute missing protein values. Secondary task: targeted panel design (pick k proteins that best predict the rest).
Cell-type classification is a sanity check only. It is not evidence for the claim.

## Mechanism (don't "improve" the method away from this)
1. Complex subunits are made in fixed ratios (stoichiometry).
2. Subunits that fail to assemble ("orphans") are degraded.
3. So co-complex proteins co-vary **at the protein level** across cells.
4. A missing subunit's abundance is partly inferable from its observed partners **in the same cell**.
5. The graph is a *prior* (edges = shared curated complexes), not something learned from this dataset.

## Repo map
- `src/scp_graphfs_mcp/`: core package. `ids.py` (ID mapping), `complexes.py` (CORUM + Complex Portal), `priors.py` (graphs + nulls), `methods.py` (imputation, propagation, selection), `datasets.py`, `registry.py` (plugin registries), `tools.py` + `server.py` (MCP).
- `contrib/<slot>/`: contributor code, one package per slot, registered via `registry.py`.
- `benchmarks/`: `run.py` + `PREREGISTRATION.md`. Protected.
- `results/`: core benchmark outputs (JSON/CSV). Protected; only `benchmarks/run.py` writes here. `results/contrib/` holds contrib outputs.
- `data/`: `raw/` snapshots, `derived/`, `datasets/`, `PROVENANCE.md`. `data/cache/` is gitignored.
- `tests/`: core + acceptance tests. `tests/contrib/` holds contributor-added tests.
- `docs/`: `SLOTS.md`, `ONBOARDING.md`, `specs/`, `glossary.json`, prior art.
- `dashboard/`: static site; reads `results/*.json` at build time.
- `demo/`, `submission/`: agent transcripts, hackathon deliverables.

## Invariants (never break; escalate instead)
- AnnData convention: cells=`obs`, proteins=`var`, `X` = log2 intensity with `NaN` for missing, `layers['raw']` = linear intensities (`X == log2(raw)`). Never fill NaN with 0.
- Fixed seeds everywhere. Same command → same `results/`.
- Every prior gets its degree-preserving shuffled null (`priors.shuffled_null`). Report it next to the real prior.
- Core `results/` is written only by `benchmarks/run.py` without `--include-contrib`. Contributions write to `results/contrib/`.
- Every downloaded file gets a row in `data/PROVENANCE.md` (URL, release, date, SHA-256).
- No fabricated citations, IDs, numbers or expected test values. Derive expected values from the snapshots in-test.
- Resource guards (`scp_prep.check_resources`) stay in front of dense/heavy steps.

## You may touch
`contrib/<your-slot>/`, `tests/contrib/`, your own docs, and `docs/glossary.json` (slot S6).

## You must not touch (CODEOWNERS: Amit-only)
`src/scp_graphfs_mcp/**` (incl. `priors.py`, `server.py`, `tools.py`, `registry.py`), `benchmarks/**`, `results/**` (except via `run.py --include-contrib` → `results/contrib/`), `data/**`, `tests/test_*.py` acceptance tests (you may add, not weaken), `AGENTS.md`, `.github/**`.

## Commands
```bash
pip install -e ".[dev]"                      # install (Python >= 3.11)
pytest -q                                    # all tests (add -m "not network" offline)
python benchmarks/run.py                     # core benchmark -> results/
python benchmarks/run.py --include-contrib   # + contrib entries -> results/contrib/ only
scp-graphfs-mcp                              # MCP server (stdio), core tools
scp-graphfs-mcp --enable-contrib variant_to_complexes
python scripts/mcp_smoke.py                  # spawn server, call tools once
# logs/scratch: write under benchmarks/_quick_out/ (gitignored), never repo root or /
cd dashboard && npm ci && npm run build      # static dashboard -> dashboard/out
./scripts/fetch_data.sh                      # re-download snapshots + verify SHA-256
```

## How to add a prior (`contrib/<slot>/__init__.py`)
```python
import networkx as nx
from scp_graphfs_mcp.complexes import CORUM_PATH          # or your own snapshot under data/
from scp_graphfs_mcp.priors import file_sha256
from scp_graphfs_mcp.registry import register_prior

def build(protein_ids: list[str]) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(protein_ids)
    g.add_edge(protein_ids[0], protein_ids[1], weight=1.0)   # weight > 0, no self-loops
    g.graph["provenance"] = {"source": "MySource", "version": "v1", "url": "https://...",
                             "sha256": file_sha256(CORUM_PATH)}   # must match a data/PROVENANCE.md row
    return g                                                      # coverage stats are added for you

register_prior("my_prior", build, "one-line description")   # shuffled null added automatically
# check it: python benchmarks/run.py --include-contrib --quick  -> results/contrib/ (look for my_prior__null0)
```

## How to add a method
```python
from scp_graphfs_mcp.registry import register_method

def select(adata, graph, k):          # -> list of k var_names
    return list(adata.var_names[:k])

def impute(adata, graph):             # -> AnnData; fill only NaN entries of X
    out = adata.copy(); ...; return out

register_method("my_method", "one-line description", select=select, impute=impute)
```

## How to add a dataset
```python
from scp_graphfs_mcp.registry import register_dataset
from scp_graphfs_mcp.datasets import from_log2_matrix   # builds X + layers['raw'] correctly

def load():
    X, cells, proteins, obs = ...     # log2 values, NaN = missing; source logged in PROVENANCE
    return from_log2_matrix(X, cells, proteins, obs=obs)

register_dataset("my_dataset", load, "one-line description")   # validated by validate_dataset
```

## How to add an MCP tool
```python
from scp_graphfs_mcp.registry import register_tool

def my_tool(query: str) -> dict:      # never raise on bad input: return {"error": {...}}
    return {"query": query, "result": []}

register_tool("my_tool", my_tool, "what it does",
              {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
# mounted only with: scp-graphfs-mcp --enable-contrib my_tool
```

## Definition of done (= merge gate)
- All tests pass and CI is green.
- One real run transcript or output file is included.
- A 3-sentence PR description gives what and why, and discloses AI assistance.
- Only allowed paths are touched.
- Amit merges.

## Current status (update at every merge)
- Headline: phase-1 test 1 FAILS (priors beat nulls, lose to kNN). Phase 2–3 (v2–v5, three datasets): no prior-based imputer beats data-only methods by a meaningful margin. Curated graphs robustly beat shuffled nulls. 'Curated partners > data-derived partners' is consistent but small (not confirmed at 1% SESOI on SCoPE2). See README §2b and docs/EXPLORATION_LOG.md.
- Core MCP tools live: `get_complexes`, `explain_protein`, `build_prior`, `propagate_scores`, `impute_with_prior`, `select_panel`.
- Slots: S1 taken (Eeshan Khan, checkpoint Oct 21 14:00 ET). S2–S7 open (`docs/SLOTS.md`).
- Known limitations: one dataset (Petrosius 2023, 215 cells); much co-variation is broad rather than complex-specific (a per-cell-normalised exploratory rerun gave the same verdict); curated-database coverage bias; masked observed values under-represent true dropouts; HVP picks likely contaminants (keratins).

## Phase 2 (exploration in progress)
`benchmarks/EXPLORATION.md` is the protocol. Use only the dev mask seeds 100–102 via `benchmarks/explore.py`.
**Never run confirmation seeds 1000–1004**: they are used once, after `PREREGISTRATION_v2.md` is committed.
Log every dev result, failures included, in `docs/EXPLORATION_LOG.md` and on the idea's issue.

## Scope guard
This project is **not** multi-omics integration, **not** a GNN embedding of the data, and **not** a general knowledge-graph platform. Ideas outside the thesis go to `docs/SLOTS.md` as proposals, not code.

## Escalate to the human (Amit) when
- an invariant would need to change;
- a test seems wrong (don't edit it, ask);
- a data source is unreachable or its release changed;
- you'd need a new dependency.
