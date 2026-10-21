# Contributing

Every contribution is **additive, isolated, tests-first and cuttable**. A great contribution saves
the team hours. A weak one costs one unmerged branch and nothing else.

## Workflow
`claim a slot → branch → code in contrib/<slot>/ → acceptance tests pass → PR → Amit merges`

1. **Claim a slot first** in `docs/SLOTS.md`: comment on its issue or ask Amit. To propose a new
   slot, ask the same way. Don't start until a spec and tests exist.
2. **One branch per person:** `contrib/<name>-<slot>` (e.g. `contrib/eeshan-s1`). If you lack push
   access, fork the repo and open the PR from your fork.
3. **Write code only in** `contrib/<slot>/`, `tests/contrib/` and your own docs.
4. **Protected paths** (Amit-only, see `.github/CODEOWNERS`): `src/scp_graphfs_mcp/priors.py`,
   `server.py`, `tools.py`, `registry.py`, `benchmarks/`, `results/`,
   `benchmarks/PREREGISTRATION.md`, `AGENTS.md`, `data/`.
5. **Tests are the contract.** Amit writes or approves the acceptance tests before implementation.
   You may *add* tests, but never weaken or delete them.
6. **Time box + checkpoint.** Each slot lists one. Missing it means the slot stays unmerged and is
   cut, with no hard feelings and no debate.
7. **Merge gate:**
   - all tests pass and CI is green;
   - one real run transcript or output file is included;
   - a 3-sentence PR description says *what* and *why*.

   Amit merges.
8. **AI assistance is welcome, and it must be disclosed** in the PR. You must be able to explain any
   line when asked. The stated "why" for a design choice must match the code.
9. **Never fabricate.** No invented citations, IDs, numbers or expected test values. Data comes only
   from documented sources, logged in `data/PROVENANCE.md` (ask Amit to add a row).
10. **No new dependencies** without approval. Keep runtime laptop-scale.
11. **Credit:** every merged contribution gets a named line in `CONTRIBUTORS.md` and the README.
    Unmerged work is credited as "explored" if you want.

## How contributions plug in
Through registries in `src/scp_graphfs_mcp/registry.py` (`PRIORS`, `METHODS`, `DATASETS`, `TOOLS`),
never by editing core code. See `AGENTS.md` for a 10-line example per registry.

- Contributed **priors** automatically get the degree-preserving shuffled null. You can't opt out.
- Contrib entries run in the benchmark only with `--include-contrib`, and write only to
  `results/contrib/`. Core headline numbers can never be changed by a contribution.
- Contrib **tools** are mounted on the MCP server only when enabled (`--enable-contrib <name>`).

## Collaborator A: hard-filter arm
`select_features(adata, graph, k, mode="hard_filter" | "soft_weight" | "none")` lives in
`scp_graphfs_mcp.methods`. `soft_weight` and `none` are implemented in the core. `hard_filter` is
**yours**: implement it in `contrib/hard_filter/` and register it with
`register_method("hard_filter", ..., select=...)`. The core `mode="hard_filter"` dispatches to it
only if it is registered. The spec is in `contrib/hard_filter/README.md`, and the contract is
`tests/test_hard_filter.py` (xfail until registered).

## Local checks before a PR
```bash
pip install -e ".[dev]"
pytest -q
python benchmarks/run.py --include-contrib --quick   # must leave results/ untouched
```
