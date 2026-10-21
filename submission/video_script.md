# 2-minute demo script

Every number below comes from `results/` (README headline). Re-read it before recording.

**0:00–0:20 · Problem.** In single-cell proteomics, a large share of the values in each cell are
missing, often because they fall below the detection limit (the usual assumption; we didn't test it). *Screen: the missingness heat-map, or the dashboard
Overview.* "Can biology fill the gaps?"

**0:20–0:45 · Mechanism.** Proteins work in machines. The proteasome's subunits are made in fixed
ratios, and unassembled subunits get degraded. So partners should rise and fall together, and a
missing subunit might be inferable from its measured partners. *Screen: dashboard → Mechanism.*

**0:45–1:15 · Live agent call.** *Screen: Claude Code with the `scp-graphfs` MCP server.* Ask:
"Which proteins in this panel act as a unit, and which missing values can be inferred from their
partners?" Show:
- `select_panel` returning complex-based justifications;
- `impute_with_prior` reporting how many values came from partners vs. kNN;
- the agent's answer saying what the tools *cannot* tell it.

(Transcript: `demo/agent_session.md`.)

**1:15–1:45 · Result.** *Screen: dashboard → Results.* "We preregistered the test. Every network prior,
STRING included, beat a shuffled version of itself, and Complex Portal had the lowest error. But plain kNN beat every
prior, so our headline hypothesis failed. And random panels beat prior-guided ones."

**(optional, +15 s) · We tried hard to make it true, honestly.**
- 6 new ideas: residual stacking, stoichiometry, graph-regularised matrix factorisation, gating, fusion, sensor-placement panels.
- Each was developed on dev masks, then preregistered and confirmed once on held-out data from two new datasets.
- Verdict: curated complexes beat shuffles, and they beat data-derived partners on Leduc. But nothing meaningfully beats kNN or low-rank models.

**1:45–2:00 · Limitations and ask.**
- One dataset.
- Much protein co-variation is shared broadly, not complex-specific. A per-cell-normalised exploratory rerun gave the same verdict.
- Curated databases are biased toward well-studied proteins.

"Everything's open and preregistered. Grab a slot in `docs/SLOTS.md`."
