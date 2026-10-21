"""Write the README headline block from results/*.json (no hand-typed numbers).

Usage: python scripts/update_readme_headline.py   (rewrites the HEADLINE block in README.md)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
imp = json.loads((R / "imputation.json").read_text())
panel = json.loads((R / "panel.json").read_text())
stab = json.loads((R / "stability.json").read_text())
clf = json.loads((R / "classification.json").read_text())
v = json.loads((R / "verdicts.json").read_text())
cov = json.loads((R / "coverage.json").read_text())
meta = json.loads((R / "run_meta.json").read_text())
import pandas as pd  # noqa: E402
dq = pd.read_csv(R / "discordant_subunits.csv")[["null_mean_r", "r_with_partners"]].quantile([0.25, 0.5, 0.75])

PRIORS = ["complexportal", "corum", "string", "string_exp"]
LABEL = {"complexportal": "Complex Portal", "corum": "CORUM", "string": "STRING (combined ≥700)",
         "string_exp": "STRING (experimental ≥700)"}


def comp(mask, prior, vs, stratum="in_complex"):
    return next(c for c in imp["masks"][mask]["comparisons"]
                if c["prior"] == prior and c["vs"] == vs and c["stratum"] == stratum)


def row(mask, method, stratum):
    return next(r for r in imp["masks"][mask]["rows"] if r["method"] == method and r["stratum"] == stratum)


def ci(c):
    return f"{c['delta_rmse']:+.3f} [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]"


def yn(b):
    return "**pass**" if b else "**fail**"


d = cov["_dataset"]
lines = [
    f"Dataset: {d['n_cells']} cells × {d['n_proteins']} protein groups, {d['missing_fraction']:.1%} missing; "
    f"{d['n_in_complex']} proteins are in ≥1 curated complex. 5 seeds × 2 masks, 10% of observed values masked; "
    f"10 shuffled nulls per prior; 95% paired-bootstrap CIs. Run: `{meta['code_commit'][:7]}`, {meta['runtime_seconds']:.0f} s.",
    "",
    "**Imputation, proteins in a curated complex (RMSE, lower is better; Δ = prior − reference, 95% CI):**",
    "",
    "| Prior | Mask | RMSE | kNN | Δ vs kNN | own null (mean) | Δ vs own null |",
    "|---|---|---|---|---|---|---|",
]
for mask in ["MCAR", "MNAR"]:
    for p in PRIORS:
        k, n = comp(mask, p, "knn"), comp(mask, p, "own_null_mean")
        lines.append(f"| {LABEL[p]} | {mask} | {k['rmse_prior']:.3f} | {k['rmse_ref']:.3f} | {ci(k)} | "
                     f"{n['rmse_ref']:.3f} | {ci(n)} |")
nk = {m: row(m, "knn", "not_in_complex")["rmse"] for m in ["MCAR", "MNAR"]}
ns = {m: row(m, "string", "not_in_complex")["rmse"] for m in ["MCAR", "MNAR"]}
lines += [
    "",
    f"Not in a complex, the curated priors fall back to kNN, so they are identical to it "
    f"(MCAR {nk['MCAR']:.3f}, MNAR {nk['MNAR']:.3f}). STRING has partners for these proteins and is worse "
    f"there (MCAR {ns['MCAR']:.3f}, MNAR {ns['MNAR']:.3f}).",
    "",
    "**Preregistered verdicts:**",
    "",
    f"- **Test 1 (headline): complex prior beats kNN *and* its own null, in-complex, on both masks:** "
    f"{yn(v['test1_pass'])}.",
    "  - Every prior beats its own shuffled null, so the curated graph structure carries real signal.",
    "  - No prior beats kNN imputation, which uses whole-cell similarity, so \"better than data alone\" is not supported.",
]
p50 = panel["50"]["all"]
lines += [
    f"- **Test 2: panel design beats HVP and the null:** {yn(v['test2_pass'])}. Complex-propagated panels won "
    f"{v['test2_wins_out_of_3']['corum']}/3 (CORUM) and {v['test2_wins_out_of_3']['complexportal']}/3 (Complex Portal) k values.",
    f"  - At k=50, mean held-out R² was {p50['complexportal']:.3f} for Complex Portal, {p50['corum']:.3f} for CORUM, "
    f"{p50['hvp']:.3f} for HVP and {p50['random_mean']:.3f} for **random panels**.",
    "  - Random beat every scored panel at k=25 and k=50. The HVP seed scores favour high-variance proteins, including likely contaminants.",
    f"- **Test 3: stability (k=50, Jaccard):** {yn(v['test3_pass'])}, by a negligible margin.",
    f"  - Complex Portal {stab['complexportal']:.3f} vs HVP {stab['hvp']:.3f} vs its null {stab['complexportal__null_mean']:.3f}.",
    f"  - CORUM {stab['corum']:.3f} (fail).",
    f"- **Test 4: curated ≥ STRING-exp ≥ STRING on in-complex RMSE:** {yn(v['test4_pass'])}. Complex Portal is best of the "
    "four priors on both masks, but STRING-combined beats STRING-experimental.",
    f"- **Sanity (classification, k=50, macro-F1, not evidence):** HVP {clf['hvp']:.3f}, random {clf['random_mean']:.3f}, "
    f"Complex Portal {clf['complexportal']:.3f}, all proteins {clf['all_proteins_detected_ge_50pct']:.3f}. "
    f"Ceiling flag: {clf['ceiling_flag']}.",
    "",
    f"**Caveat found after the run (not preregistered):** for well-measured complex proteins, the weighted mean of "
    f"*shuffled-null* partners already correlates with the protein at median r = {dq['null_mean_r'][0.5]:.2f} "
    f"(IQR {dq['null_mean_r'][0.25]:.2f}–{dq['null_mean_r'][0.75]:.2f}), against median r = {dq['r_with_partners'][0.5]:.2f} "
    "for real curated partners (`results/discordant_subunits.csv`). That suggests a strong cell-wide abundance factor "
    "in these per-cell-unnormalised values, which kNN exploits. A normalised rerun would be a separate, exploratory analysis.",
]
text = (ROOT / "README.md").read_text()
a, b = text.index("<!-- HEADLINE:START -->"), text.index("<!-- HEADLINE:END -->")
(ROOT / "README.md").write_text(text[:a] + "<!-- HEADLINE:START -->\n" + "\n".join(lines) + "\n" + text[b:])
print("\n".join(lines))
