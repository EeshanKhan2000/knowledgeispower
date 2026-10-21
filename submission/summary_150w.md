# Community-paper paragraph (≤150 words)

**scp-graphfs-mcp: do curated protein complexes help reconstruct single-cell proteomes?**
We tested whether curated complex membership (CORUM, Complex Portal) is a better prior for imputing missing
single-cell proteomics values than data alone, STRING, or degree-preserving shuffles. Every test was
preregistered and run once, on held-out masks from three datasets (Petrosius 2023, Leduc 2022, Specht 2021).

**Results:**
- **Shuffles:** curated graphs consistently beat their own shuffles.
- **Data-derived partners:** Complex Portal partners beat data-derived partners on Leduc (3–5%), but by under the preregistered 1% threshold on SCoPE2.
- **Data-only imputers:** no prior-based method beat kNN or low-rank completion by a meaningful margin, so the headline hypothesis was not supported.

We release the benchmark, the provenance, the negative results and an MCP server that lets LLM agents run these analyses:
github.com/xX-its-amit-Xx/knowledgeispower.
