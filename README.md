# scp-graphfs-mcp

## 1. Claim

> Curated protein-complex membership (CORUM, EBI Complex Portal) is a better prior for **reconstructing a cell's protein state from incomplete single-cell proteomics measurements** than data alone, than generic PPI networks (STRING), and than a degree-preserving shuffled version of the same graph.

**Why it could be true:** complex subunits are made in fixed ratios, and subunits that fail to assemble are degraded. So co-complex proteins co-vary at the protein level, more than their mRNAs do (Gonçalves et al., *Cell Systems* 2017, [10.1016/j.cels.2017.08.013](https://doi.org/10.1016/j.cels.2017.08.013)). That makes a missing subunit partly inferable from its measured partners.

## 2. Headline result

<!-- HEADLINE:START -->
*Filled from `results/` after the preregistered run.*
<!-- HEADLINE:END -->

The design was preregistered in [`benchmarks/PREREGISTRATION.md`](benchmarks/PREREGISTRATION.md), committed before any benchmark ran. Every row, including losses, is in `results/*.json` and on the dashboard.

## 3. Quickstart

```bash
git clone https://github.com/xX-its-amit-Xx/knowledgeispower && cd knowledgeispower
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
pytest -q -m "not network"
python benchmarks/run.py                  # ~6 min on a laptop -> results/
scp-graphfs-mcp                           # MCP server over stdio
claude mcp add scp-graphfs -- "$PWD/.venv/bin/scp-graphfs-mcp"   # connect Claude Code
```

The MCP tools are `get_complexes`, `explain_protein`, `build_prior`, `propagate_scores`, `impute_with_prior` and `select_panel`. See a real session in [`demo/agent_session.md`](demo/agent_session.md).

## 4. Prior art and differentiation

All entries were verified by fetching DOI metadata or pages; full list (35 entries) and query log in [`docs/prior-art.json`](docs/prior-art.json) and [`docs/prior-art-search-log.md`](docs/prior-art-search-log.md).

| Work | Class | How we differ |
|---|---|---|
| **GIRAFI** (bioRxiv 2026, [10.64898/2026.05.18.726081](https://doi.org/10.64898/2026.05.18.726081)) | **Direct overlap** | Graph-prior imputation for SCP **already exists**. It uses a STRING prior, and in the text we fetched we found no shuffled-network control. We test *which* prior (curated complexes vs. STRING vs. a degree-preserving null) |
| Petrosius et al., *MCP* 2025 ([10.1016/j.mcpro.2025.100982](https://doi.org/10.1016/j.mcpro.2025.100982)) | Direct overlap (mechanism) | Shows known complexes co-vary in Astral SCP data, descriptively. We use that co-variation as a prior and benchmark it |
| Fuzzy-FishNET, Goh, *BMC Med Genomics* 2016 ([10.1186/s12920-016-0228-z](https://doi.org/10.1186/s12920-016-0228-z)) | Direct overlap | Complex-based feature selection, but on bulk proteomics for class discrimination |
| Protrec2, *Brief Bioinform* 2025 ([10.1093/bib/bbaf692](https://doi.org/10.1093/bib/bbaf692)) | Direct overlap | Complex membership to recover missing proteins, but in bulk data and predicting detection, not single-cell abundance |
| NIFty (bioRxiv 2026, [10.64898/2026.03.06.710179](https://doi.org/10.64898/2026.03.06.710179)) | Direct overlap (task) | Missingness-tolerant SCP feature selection with no prior. Candidate baseline (slot S4) |
| GEARS, *Nat Biotechnol* 2024 ([10.1038/s41587-023-01905-6](https://doi.org/10.1038/s41587-023-01905-6)) | Adjacent | Transcriptomic perturbation prediction with GO and co-expression graphs; no complex prior |
| Wefers et al., *Nat Methods* 2026 ([10.1038/s41592-026-03142-6](https://doi.org/10.1038/s41592-026-03142-6)) | Adjacent | A localisation-prediction benchmark where generic PPI (STRING/BioPlex) GraphSAGE gave no substantial gain. Not SCP |
| AROMA (arXiv [2604.20263](https://arxiv.org/abs/2604.20263)) | Adjacent | Merges STRING and CORUM into one graph for perturbation reasoning. We keep the sources separate and test each against a null |
| PRINCE, *PLoS Comput Biol* 2010 ([10.1371/journal.pcbi.1000641](https://doi.org/10.1371/journal.pcbi.1000641)) | Building block | Network propagation; our RWR panel scoring follows it |
| STRING MCP ([string-db.org/help/mcp](https://string-db.org/help/mcp/)), ToolUniverse (arXiv [2509.23426](https://arxiv.org/abs/2509.23426)) | Building block | Agent access to STRING and to Complex Portal lookups already exists. A bare complex-lookup MCP server is not novel |
| MCPmed (arXiv [2507.08055](https://arxiv.org/abs/2507.08055)) | Collaborator | MCP wrappers for GEO, STRING and the UCSC Cell Browser. Our server could join |
| CORUM ([10.1093/nar/gkae1033](https://doi.org/10.1093/nar/gkae1033)), Complex Portal ([10.1093/nar/gkae1085](https://doi.org/10.1093/nar/gkae1085)), STRING ([10.1093/nar/gkae1113](https://doi.org/10.1093/nar/gkae1113)) | Data sources | Snapshots, versions and SHA-256 in [`data/PROVENANCE.md`](data/PROVENANCE.md) |

**Corrected from our starting notes:**
- Wefers 2026 is not an SCP paper.
- The Leduc 2022 nPOP paper does not analyse complex co-variation.
- The complex-attenuation paper's first author is Gonçalves.
- AROMA and MAP-KG are unrelated works.

## 5. What's novel, narrowly

Four things together:
- curated complex priors (CORUM and Complex Portal, each tested separately against STRING);
- the single-cell proteomics reconstruction tasks: imputation under MCAR and MNAR masks, and panel design;
- a degree-preserving shuffled-graph null for every prior;
- an MCP interface so an LLM agent can run it.

None of the pieces is new alone.

## 6. Limitations

- **Coverage:** curated databases have limited coverage and favour well-studied proteins.
  - Only ~1100 of 2813 proteins here have any curated-complex partner.
  - CORUM is mammal-centric.
- **One dataset:** 215 cells of one AML model (Petrosius et al. 2023 preprint, [10.1101/2023.06.06.543943](https://doi.org/10.1101/2023.06.06.543943)).
- **Masking undercounts the hardest cases:** masked *observed* values under-represent the hardest true dropouts. Our MNAR mask only mimics them.
- **`layers['raw']` is reconstructed** as `2**X`, because the source ships log2 values only.
- **Contaminants:** the HVP panel scores pick up keratins (likely sample contaminants), as the agent transcript shows. No contaminant filter was preregistered.
- **The CORUM null keeps ~30% of real edges.** Its large cliques restrict how far degree-preserving swaps can move, so that null is conservative.
- **Hackathon scale:** built in about one day.

## 7. Contributors

- Thesis, priors, benchmark, core MCP: **Amit Shenoy**
- Hard-filter arm: **Collaborator A** *(in progress; credited here when merged)*
- Variant→complex bridge: **Eeshan Khan** *(slot S1; listed as a contributor only if merged)*
- One line per merged slot: see [`CONTRIBUTORS.md`](CONTRIBUTORS.md)

## 8. Where you could plug in

Open slots are listed in [`docs/SLOTS.md`](docs/SLOTS.md); start with [`docs/ONBOARDING.md`](docs/ONBOARDING.md) (15 minutes). Coding agents: read [`AGENTS.md`](AGENTS.md).

| Slot | Task |
|---|---|
| S2 | Second dataset loader + cross-context test |
| S3 | Extra prior source (hu.MAP, BioPlex, ontology) |
| S4 | NIFty baseline wrapper |
| S5 | MCP client recipes |
| S6 | Glossary + dashboard explainers |
| S7 | Test hardening |

## 9. Citation and license

See [`CITATION.cff`](CITATION.cff); also cite the data sources in [`data/PROVENANCE.md`](data/PROVENANCE.md). Code is under the Apache-2.0 license. The `scp-prep` dependency is GPL-3.0-or-later, so anyone redistributing a combined build is bound by GPL terms.
