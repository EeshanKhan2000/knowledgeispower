# Community-paper paragraph (≤150 words)

**scp-graphfs-mcp: do curated protein complexes help reconstruct single-cell proteomes?**
Single-cell proteomics measurements are incomplete, and complex subunits co-vary at the protein level.
We therefore tested whether curated complex membership (CORUM, EBI Complex Portal) is a better prior
for imputing missing values than kNN, STRING, or degree-preserving shuffles of the same graphs. The
design was preregistered before any run. The data were 215 OCI-AML8227 cells (Orbitrap Astral, 40.7%
missing), with 10% of observed values masked under MCAR- and MNAR-like masks.

Every prior, STRING included, beat its own shuffled null, and Complex Portal had the lowest error of the four priors
(in-complex RMSE 0.730 vs. null 0.807). No prior beat kNN (0.687), so the headline hypothesis failed.
Prior-guided panels did not beat random panels. The tools are exposed to LLM agents through an MCP
server. Code, provenance and every result: github.com/xX-its-amit-Xx/knowledgeispower.
