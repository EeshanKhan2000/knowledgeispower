"""Write the README "Phase 2-3" block from results/phase2 and results/phase3 JSON (no hand-typed numbers).

Usage: python scripts/update_readme_phase23.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    f = ROOT / p
    return json.loads(f.read_text()) if f.exists() else None


def fmt(c):
    return (f"{c['delta_rmse']:+.4f} [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]"
            + (f" ({c['pct_of_ref_rmse']:+.2f}%)" if "pct_of_ref_rmse" in c else ""))


L = ["*Exploration protocol:* [`benchmarks/EXPLORATION.md`](benchmarks/EXPLORATION.md). Every dev result is in "
     "[`docs/EXPLORATION_LOG.md`](docs/EXPLORATION_LOG.md). Each confirmation was preregistered before its "
     "held-out data was touched, and run once.", ""]

v2 = load("results/phase2/confirm/confirm_v2.json")
if v2:
    L += [f"**v2: Petrosius held-out masks.** Primary E3 (low-rank + CORUM Laplacian): **not confirmed** "
          f"({v2['primary_passes']}). It does not beat its own shuffled null:"]
    for k, m in v2["masks"].items():
        c = next(x for x in m["comparisons"] if x["role"] == "primary" and x["vs"] == "own_null_mean")
        L.append(f"- {k}: {fmt(c)}")
    L.append("")

v3 = load("results/phase3/confirm_v3.json")
if v3:
    L += [f"**v3: independent dataset (Leduc 2022, {v3['n_cells']} cells); E6, Complex Portal residuals on low-rank.** "
          f"Passes {v3['primary_passes']} as written, but the gain is practically zero (no minimum effect size "
          "was preregistered; disclosed):"]
    for k, m in v3["masks"].items():
        for c in m["comparisons"]:
            if c["role"] == "primary":
                L.append(f"- {k} vs {c['vs']}: {fmt(c)}")
    L.append("")

v4 = load("results/phase3/confirm_v4.json")
if v4:
    L += [f"**v4: Leduc, 30-cell subsamples; data graph + Complex Portal.** **Not confirmed** "
          f"({v4['primary_passes']}). It loses to kNN. Secondary: Complex Portal partners vs. data-derived partners:"]
    for n, reg in v4["regimes"].items():
        for k, m in reg.items():
            c = next(x for x in m["comparisons"] if x["method"] == "complexportal_alone" and x["vs"] == "data_alone")
            L.append(f"- n={n} {k}: {fmt(c)}")
    L.append("")

v5 = load("results/phase3/confirm_v5.json")
if v5:
    verdict = "**CONFIRMED**" if v5["primary_confirmed"] else "**not confirmed**"
    L += [f"**v5: third dataset (SCoPE2), 30-cell subsamples, minimum effect size 1%.** The claim is narrow: *curated "
          f"Complex Portal partners beat data-derived partners and a shuffled null.* Result: {verdict} "
          f"({v5['primary_passes']})."]
    for n, reg in v5["regimes"].items():
        for k, m in reg.items():
            for c in m["comparisons"]:
                if c["method"] == "complexportal_alone" and c["vs"] in ("data_alone", "own_null_mean", "knn"):
                    tag = "" if c["role"] == "primary" else " (secondary)"
                    L.append(f"- n={n} {k} vs {c['vs']}{tag}: {fmt(c)} {'✓' if c['pass'] else '✗'}")
    L.append("")

text = (ROOT / "README.md").read_text()
a, b = text.index("<!-- PHASE23:START -->"), text.index("<!-- PHASE23:END -->")
(ROOT / "README.md").write_text(text[:a] + "<!-- PHASE23:START -->\n" + "\n".join(L) + "\n" + text[b:])
print("\n".join(L))
