# Contribution slots

Each slot is pre-scoped and off the critical path. Before anyone starts, Amit writes (or approves)
its acceptance tests. Claim one by commenting on its issue or asking Amit. Rules:
`CONTRIBUTING.md`. Agent instructions: `AGENTS.md`.

| Slot | Task | Good for | Off critical path because | Owner | Time box / checkpoint | Spec · tests |
|---|---|---|---|---|---|---|
| **S1** | Variant → complex bridge | Genomics, backend | Optional demo story | **Eeshan Khan** (@EeshanKhan2000) | Oct 21, 14:00 ET | `docs/specs/variant_bridge.md` · `tests/test_variant_bridge.py` |
| S2 | Second dataset loader + cross-context test | Data engineering | Stretch test only | *open* | 3 h | `docs/specs/S2_dataset.md` · `tests/contrib/test_s2_dataset.py` |
| S3 | Extra prior source. Candidates to *verify first*: hu.MAP, BioPlex-derived complexes, EMAPA/Cell Ontology | Bio/KG people | Goes to `results/contrib/` | *open* | 3 h | `docs/specs/S3_prior.md` · `tests/contrib/test_s3_prior.py` |
| S4 | NIFty baseline wrapper (only if its code is public) | ML people | Extra baseline row | *open* | 3 h | `docs/specs/S4_nifty.md` · `tests/contrib/test_s4_nifty.py` |
| S5 | MCP client recipes: Claude Desktop, Claude Code, one non-Claude agent framework, each with a working transcript | Agent/devtools people | Docs only | *open* | 2 h | `docs/specs/S5_recipes.md` |
| S6 | Glossary + dashboard explainer entries | Science communicators | Content in `docs/glossary.json` only | *open* | 2 h | `docs/specs/S6_glossary.md` · `tests/test_glossary.py` |
| S7 | Test hardening: edge cases, CI, type hints | Anyone careful | Can only make things safer | *open* | 2 h | `docs/specs/S7_hardening.md` |
| A | Hard-filter selection arm | Collaborator A | Extra benchmark arm | **Collaborator A** | TBD by Amit | `contrib/hard_filter/README.md` · `tests/test_hard_filter.py` |

Ideas outside the thesis (multi-omics, GNN embeddings, general KG) are logged below as proposals,
not code.

## Proposals (not scheduled)
- *(none yet)*
