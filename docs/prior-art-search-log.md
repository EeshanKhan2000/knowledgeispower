# Prior-art search log

All searches were run on 2026-10-21, inside the sandbox. Bibliographic facts in `prior-art.json` come only from pages and API responses fetched in this session: Crossref `api.crossref.org/works/<DOI>`, Europe PMC REST (`resultType=core` for abstracts, `/<PMCID>/fullTextXML` for full text), the arXiv export API and arXiv HTML, `api.biorxiv.org`, the bioRxiv full text via WebFetch, the UCLouvain Dataverse API, nature.com via curl, string-db.org, github.com via WebFetch, and zitniklab.hms.harvard.edu.

Blocked or limited sources:
- `www.biorxiv.org` returned HTTP 429 to curl every time (12 retries over about 9 minutes) and some of the time to WebFetch.
- `github.com` returned 403 to curl. The `gh` search API is blocked for this session ("sessions are bound to their configured repositories").
- `nature.com` WebFetch redirected to an IdP, but curl with a cookie jar returned the full article.

"Relevant hits" in the tables means results judged relevant to this project after reading titles and abstracts.

## Query log

### Verification queries (starting entries)

| # | Engine / API | Query | Total hits | Relevant hits |
|---|---|---|---|---|
| 1 | Crossref works API | DOIs 10.1038/s41587-023-01905-6, 10.1186/s12920-016-0228-z, 10.1093/nar/gkac1015, 10.1186/s13059-022-02817-5 | 4 records | 4 |
| 2 | Europe PMC | `AUTH:"Wefers" AND (PUB_YEAR:2025 OR PUB_YEAR:2026)` | 38 | 1 (Wefers Z et al., Nat Methods 2026) |
| 3 | Europe PMC | `AUTH:"Wefers" AND (proteomics OR protein OR perturbation)` | 122 | 1 (same) |
| 4 | Europe PMC | `"subcellular localization" AND AUTH:"Wefers Z"` | 2 | 1 |
| 5 | Europe PMC | `(GraphSAGE AND "subcellular localization" AND (BioPlex OR STRING))` | 14 | 0 |
| 6 | curl nature.com | https://www.nature.com/articles/s41592-026-03142-6, grepped for GraphSAGE/BioPlex/STRING/CORUM/ProtT5 | full text | confirmed the PPI experiment |
| 7 | Europe PMC | `AROMA AND perturbation AND (knowledge graph OR CORUM)` | 292 | 0 (food-aroma noise) |
| 8 | Europe PMC | `"MAP-KG"` | 22 | 1 (MAP, bioRxiv 2026) |
| 9 | Europe PMC | `CORUM AND STRING AND "knowledge graph" AND perturbation` | 8 | 0 |
| 10 | WebSearch | `AROMA perturbation reasoning knowledge graph STRING CORUM LLM single-cell` | 9 links | 1 (arXiv 2604.20263) |
| 11 | arXiv API + HTML | 2604.20263 (AROMA), 2507.08055 (MCPmed) | 2 | 2 |
| 12 | Europe PMC | `TITLE:"Associating genes and protein complexes with disease via network propagation"` | 1 | 1 |
| 13 | Europe PMC | `NIFty AND (single-cell proteomics OR feature selection)` | 164 | 1 |
| 14 | bioRxiv API | details/biorxiv/10.64898/2026.03.06.710179 | 1 | 1 |
| 15 | WebSearch | `NIFty single-cell proteomics top-scoring pairs github Payne` | 9 links | 0 |
| 16 | WebFetch | https://github.com/PayneLab?tab=repositories&q=nifty | page | 2 repos (nifty, nifty-manuscript) |
| 17 | WebFetch | https://www.biorxiv.org/content/10.64898/2026.03.06.710179v1.full | full text | code URLs confirmed |
| 18 | Europe PMC | `PCIPG2.0 OR "PCIPG 2.0" OR PCIPG` | 3 shown | 2 (PCIPG2.0; PCIPG, PLoS CB 2026) |
| 19 | Europe PMC | `scPROTEIN AND single-cell proteomics` | 2 shown | 1 |
| 20 | Europe PMC | `scProfiterole` | 3 shown | 2 (journal + preprint) |
| 21 | WebSearch | `STRING database official MCP server Model Context Protocol string-db` | 10 links | 2 (string-db.org/help/mcp, meringlab/string-mcp) |
| 22 | WebFetch | https://string-db.org/help/mcp/ | page | 1 |
| 23 | Europe PMC | `TITLE:CORUM AND (PUB_YEAR:2024 OR PUB_YEAR:2025 OR PUB_YEAR:2026)` | 6 | 2 (CORUM in 2024; Yang et al. BiB 2025) |
| 24 | Europe PMC | `TITLE:"Complex Portal"` | 21 | 2 (Complex Portal 2025, 2022) |
| 25 | Europe PMC | `"Complex Portal" AND JOURNAL:"Nucleic Acids Res" AND PUB_YEAR:2026` | 5 | 0 (no 2026 Complex Portal NAR paper found) |
| 26 | Europe PMC | `TITLE:"STRING database" AND AUTH:"Szklarczyk"` | 6 | 2 (2023 = v12.0, 2025 = v12.5) |
| 27 | Europe PMC | `TITLE:"Genenames.org" OR (TITLE:HGNC AND JOURNAL:"Nucleic Acids Res")` | 9 | 1 (2026 edition) |
| 28 | Europe PMC | `(attenuation OR "protein complex") AND AUTH:"Beltrao P" AND JOURNAL:"Cell Syst"` | 1 shown | 1 (Gonçalves 2017) |
| 29 | Europe PMC | `AUTH:"Sousa A" AND AUTH:"Beltrao P"` | 5 | 1 (Sousa 2019 MCP) |
| 30 | Europe PMC | `AUTH:"Petrosius V" AND (single-cell OR AML OR Astral)` | 20 | 4 |
| 31 | DOI content negotiation + Dataverse API | doi:10.14428/DVN/4DSPJM | 1 | 1 |
| 32 | bioRxiv API | details and pubs for 10.1101/2023.06.06.543943 and 10.1101/2024.07.31.605978 | 2 | 2 |
| 33 | Europe PMC full text | PMC12209951 (Petrosius MCP 2025), PMC9756690 (nPOP), PMC11180609 (GEARS) | 3 | 3 |
| 34 | WebFetch | https://www.biorxiv.org/content/10.1101/2023.06.06.543943v1.full | full text | OCI-AML8227 confirmed |
| 35 | Europe PMC | `TITLE:"Exploration of cell state heterogeneity using single-cell proteomics"` | 2 | 1 (Nat Commun 2023, not AML; see corrections) |

### New-work searches: 2025–2026

**(a) Complex-membership priors in single-cell or proteomics ML and imputation**

| # | Engine | Query | Total hits | Relevant hits |
|---|---|---|---|---|
| A1 | Europe PMC | `("single-cell proteomics" OR "single cell proteomics") AND (CORUM OR "protein complex" OR "protein complexes") AND (imputation OR "missing values") AND PUB_YEAR:[2025 TO 2026]` | 23 | 1 (Petrosius MCP 2025) |
| A2 | Europe PMC | `("single-cell proteomics") AND ("protein complex" OR CORUM) AND (prior OR "graph" OR network) AND PUB_YEAR:[2025 TO 2026]` | 46 | 0 |
| A3 | Europe PMC | `proteomics AND imputation AND (CORUM OR "protein complex membership" OR "complex-aware" OR "protein-protein interaction") AND PUB_YEAR:[2025 TO 2026]` | 694 | 4 (GIRAFI, Protrec2, Lupine, Arnaout 2026) |
| A4 | Europe PMC | `"network-based imputation" AND proteomics` | 1 | 0 |
| A5 | Europe PMC | `CORUM AND (imputation OR "missing values" OR "missing proteins") AND PUB_YEAR:[2024 TO 2026]` | 176 | 3 (Protrec2, Rosenberger 2026, plus repeats) |
| A6 | Europe PMC | `"protein complex" AND ("single-cell proteomics" OR "single cell proteomics") AND (covariation OR "co-variation" OR stoichiometry) AND PUB_YEAR:[2023 TO 2026]` | 16 | 0 |
| A7 | Europe PMC | `SRC:PPR AND ("single-cell proteomics" OR "single cell proteomics") AND (graph OR network OR "prior knowledge") AND (imputation OR "missing values") AND PUB_YEAR:[2025 TO 2026]` | 3 | 1 (GIRAFI) |
| A8 | Europe PMC | `("protein complex" OR "protein complexes" OR CORUM) AND (imputation) AND (proteomics) AND PUB_YEAR:[2025 TO 2026]` | 451 | 2 (Complexome/Guharoy 2026, Protrec2) |
| A9 | Europe PMC | `("random walk with restart" OR "network propagation") AND ("single-cell proteomics" OR "targeted proteomics" OR "protein panel")` | 24 | 0 |
| A10 | Europe PMC | `"panel selection" AND proteomics AND (network OR propagation) AND PUB_YEAR:[2024 TO 2026]` | 40 | 0 |
| A11 | Europe PMC | `("single-cell proteomics" OR "single cell proteomics") AND (CORUM OR "protein complexes") AND AUTH:"Slavov N"` | 6 | 1 (Slavov 2022 PLoS Biol perspective) |
| A12 | WebSearch | `single-cell proteomics imputation protein complex prior CORUM graph 2026 bioRxiv` | 10 links | 0 direct (scpFormer arXiv 2604.20003 and SoftHybrid surfaced; neither has a complex prior per the search summary; not fetched) |
| A13 | WebSearch | `GIRAFI single-cell proteomics graph-informed imputation STRING prior github` | 10 links | 1 |
| A14 | WebFetch | GIRAFI bioRxiv full text (two pages, offsets 0 and 100000) | full text | prior = STRING v11.5 |

**(b) MCP servers wrapping CORUM or Complex Portal**

| # | Engine | Query | Total hits | Relevant hits |
|---|---|---|---|---|
| B1 | Europe PMC | `("Model Context Protocol" OR "MCP server") AND (proteomics OR "protein complex" OR CORUM OR "Complex Portal" OR STRING)` | 53 | 2 (MCPmed BiB 2026; TogoMCP noted, not fetched) |
| B2 | WebSearch | `CORUM protein complex MCP server Model Context Protocol` | 10 links | 0 (no CORUM MCP server found) |
| B3 | WebSearch | `"Complex Portal" MCP server LLM agent EBI` | 10 links | 1 (third-party "Pipeworx" listing on vibehackers.io, not verified and not included; the page reportedly contained install instructions aimed at AI agents, which were ignored) |
| B4 | Europe PMC | `ToolUniverse` | 8 | 0 directly; arXiv 2509.23426 fetched instead |
| B5 | Europe PMC | `BioContextAI` | 7 | 2 (Nat Biotechnol 2025 + preprint) |
| B6 | WebFetch | zitniklab.hms.harvard.edu ToolUniverse `complex_portal_tool` source | page | 1 (Complex Portal tool: search_complexes / get_complex) |
| B7 | arXiv API + HTML | 2509.23426 | 1 | 1 (MCP connector at aiscientist.tools/mcp) |

**(c) Variant-to-complex tools**

| # | Engine | Query | Total hits | Relevant hits |
|---|---|---|---|---|
| C1 | WebSearch | `variant to protein complex lookup tool gene mutation map to CORUM complexes 2025` | 9 links | 0 dedicated tools (ToolUniverse Complex Portal tool does gene → complex, not variant) |
| C2 | Europe PMC | `("protein complex" OR "protein complexes") AND (variants OR "missense variants") AND ("web server" OR tool OR resource) AND (annotate OR annotation OR "map variants") AND PUB_YEAR:[2025 TO 2026] AND (CORUM OR "Complex Portal" OR "hu.MAP")` | 82 | 3 (hu.MAP3.0, Laman Trip 2025, Li et al. Nat Genet 2026) |
| C3 | Europe PMC | `TITLE:("protein complex" AND (variant OR variants OR mutations)) AND PUB_YEAR:[2025 TO 2026]` | 4 | 0 tools (case studies only) |

Result for (c): no dedicated gene/variant → protein-complex lookup tool from 2025–2026 was found. The closest items are the ToolUniverse Complex Portal tool (gene → complex) and Li, Li & Liu, Nat Genet 2026 (trans-pQTLs mapped to PPI clusters).

## Corrections to the starting descriptions

1. **GEARS.** The description was correct (GO-derived graph plus co-expression graph; the full text has no CORUM/STRING). Crossref lists the issue as Nat Biotechnol **42(6):927-935, 2024**, published online 2023-08-17.
2. **Wefers et al., Nat Methods 2026.** This paper is **"A comprehensive benchmark of sequence-based subcellular localization predictors for human proteins"** by Wefers Z, Gupta A, Ahmed N, Zhang X and Lundberg E, Nat Methods 23(7):1458-1469, DOI 10.1038/s41592-026-03142-6.
   - The PPI detail is correct. GraphSAGE layers on ProtT5-MHA, trained on BioPlex 3.0 or STRING, "did not substansially outperform ProtT5-MHA by any average metric".
   - The task is **protein subcellular localization**, not single-cell proteomics or cell-state reconstruction.
   - **Reclassified from "most important collision" to Adjacent.** It is useful as negative evidence on generic-PPI GNN priors.
3. **AROMA / MAP-KG.** These are **two unrelated works**, not one entry.
   - AROMA: Wang, Ye, Liu & Ng, arXiv 2604.20263, ACL 2026 Findings. Its Gene-KG merges STRING with CORUM complexes expanded to pairwise edges, and evidence types are collapsed into one graph. Verified in the arXiv HTML.
   - MAP / MAP-KG: Feng et al., bioRxiv 2026, 10.64898/2026.02.25.708091. A drug-response KG built from 14 resources; whether CORUM is among them is unverified.
   - Classified as Adjacent: the knowledge sources overlap, but the task is transcriptional perturbation prediction.
4. **Fuzzy-FishNET.** Correct: sole author Goh WWB, BMC Med Genomics 9(Suppl 3):67, December 2016.
5. **PRINCE.** Correct: Vanunu, Magger, Ruppin, Shlomi & Sharan, PLoS Comput Biol 6(1):e1000641, 2010. Note that PRINCE **also infers disease-associated protein complexes**, not just genes.
6. **NIFty.** Correct: bioRxiv 2026, Nitz, Echarry, McGee & Payne, top-scoring pairs, no imputation.
   - Code is public at https://github.com/PayneLab/nifty, with manuscript code at https://github.com/PayneLab/nifty-manuscript.
   - New detail: NIFty already benchmarks on Petrosius et al. data (MassIVE MSV000095333, Exp6).
7. **PCIPG2.0.** Correct: Huang, Wang, Yang & Gong, Bioinformatics 42(8):btag552, 2026. It is evaluated on yeast benchmarks. A companion paper, PCIPG, appeared in PLoS Comput Biol 2026 (10.1371/journal.pcbi.1014698).
8. **scPROTEIN and scProfiterole.**
   - scPROTEIN: Li W et al., Nat Methods 21(4):623-634, 2024. The abstract says "graph contrastive learning" for cell embeddings but does not specify a cell–cell graph, so that detail is unverified.
   - scProfiterole: Coşkun et al., J Comput Biol (online 2026-10-09). Its cell-to-cell similarity graphs are confirmed in the abstract.
9. **STRING MCP.** The official server is https://mcp.string-db.org/ (documented at https://string-db.org/help/mcp/), with self-hosting code at https://github.com/meringlab/string-mcp (MIT).
10. **MCPmed.** Correct (GEO, STRING, UCSC Cell Browser). It is now also published as Brief Bioinform 27(1):bbag076 (2026). Code: https://github.com/MCPmed.
11. **CORUM.** The 2022 paper's title is "CORUM: the comprehensive resource of mammalian protein complexes–**2022**", published in NAR 51(D1):D539-D545 (2023), which the starting description had right. The update is **"CORUM in 2024: protein complexes as drug targets"**:
    - Authors: Steinkamp R, Tsitsiridis G, Brauner B, Montrone C, Fobo G, Frishman G, Avram S, Oprea TI, Ruepp A.
    - Published in NAR **53(D1):D651-D657**, DOI **10.1093/nar/gkae1033**.
    - It describes CORUM 5.0 (7,193 complexes).
12. **Complex Portal.** The most recent NAR paper found is **"Complex portal 2025: predicted human complexes and enhanced visualisation tools..."**:
    - Balu S et al., NAR 53(D1):D644-D650, DOI **10.1093/nar/gkae1085**.
    - No 2026 Complex Portal NAR paper was found.
    - It includes 14,964 ML-predicted hu.MAP3.0 complexes alongside 2,150 curated human complexes.
13. **Beltrao Cell Systems 2017.** The first author is **Gonçalves E**, not Sousa: "Widespread Post-transcriptional Attenuation of Genomic Copy-Number Variation in Cancer", Cell Syst 5(4):386-398.e4. Sousa A is first author of the follow-up, Mol Cell Proteomics 18(8):S114-S125 (2019); both are included. The Gonçalves abstract supports post-transcriptional buffering enriched in complex members and co-regulation of subunits. The exact phrase "co-regulated at protein more than mRNA level" is our paraphrase.
14. **nPOP (Leduc et al., Genome Biol 23:261, 2022).** The bibliographic details are correct, but the hypothesis that it shows protein-complex covariation in single cells is **not supported**.
    - The full text (PMC9756690) mentions "complex" once, in an introductory sentence ("protein covariation may reflect protein interactions within complexes").
    - The results cover cell-cycle and metabolic/ribosomal covariation.
    - Downgraded from Direct overlap to weak Mechanistic support.
15. **Petrosius et al. 2023 (our dataset).** The correct citation is the **bioRxiv preprint** "Evaluating the capabilities of the Astral mass analyzer for single-cell proteomics", Petrosius V et al. (15 authors), DOI **10.1101/2023.06.06.543943**, posted 2023-06-08.
    - The Dataverse record doi:10.14428/DVN/4DSPJM ("Astral AML single-cell data from Petrosius et al. 2023 preprint") cites it explicitly.
    - Its full text names OCI-AML8227.
    - The bioRxiv API reports no published version linked to this preprint.
    - Do **not** cite Petrosius et al., Nat Commun 14:5910 (2023), DOI 10.1038/s41467-023-41602-1. That paper is Orbitrap DIA on mouse ES cells, not AML.
    - The related journal paper, Petrosius et al., Mol Cell Proteomics 24(6):100982 (2025), is the published form of a different preprint (10.1101/2024.07.31.605978). It uses HEK293/U937/BM CD34+ cells, not OCI-AML8227, and **does show covariation of known complexes (MCM, proteasome) in Astral SCP**, which makes it a direct mechanistic overlap.
16. **STRING.** The v12.0 paper is Szklarczyk et al., NAR 51(D1):D638-D646 (2023), DOI 10.1093/nar/gkac1000. The **v12.5 paper exists**: "The STRING database in 2025: protein networks with directionality of regulation", NAR 53(D1):D730-D737, DOI 10.1093/nar/gkae1113. The STRING 2023 abstract states that STRING integrates "known complexes/pathways from curated sources", so the STRING baseline already partly contains curated complex information.
17. **HGNC.** The most recent paper is "Genenames.org: the HGNC and PGNC resources in 2026", Seal RL et al., NAR 54(D1):D1098-D1107, DOI 10.1093/nar/gkaf1229.

## Unverified items

- **MAP-KG components** (whether CORUM is included): only the abstract was read; the bioRxiv full text was not fetched.
- **scPROTEIN graph type** (cell–cell vs other): only the abstract was read.
- **BioContextAI server contents** (which knowledgebases): only the preprint abstract (api.biorxiv.org) and the Crossref record were read. The STRING/OmniPath/Reactome list came from a WebSearch summary, not a primary page.
- **Third-party Complex Portal MCP listing** (vibehackers.io, "Pipeworx"): seen only in a WebSearch summary. Not fetched, not included in the JSON.
- **scpFormer (arXiv 2604.20003) and SoftHybrid (J Proteome Res 2026)**: surfaced in a WebSearch summary only. Not fetched or verified, and not included in the JSON.
- **GIRAFI ablations**: the full text says "ablations supported the graph-informed design", but no shuffled or degree-preserving network control was found in the fetched text. GIRAFI code is announced at https://github.com/dorothyzh/GIRAFI, but that repository was not fetched.
