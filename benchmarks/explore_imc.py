"""Amendment-5 DEV runs: knowledge-derived protein representations in side-information matrix completion.

    python benchmarks/explore_imc.py   -> results/phase5/dev/dev_imc.json (+ summary)

Leave-one-dataset-out for corpus features; dev seeds 100-102 only; holdouts never touched.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import make_mask  # noqa: E402

from scp_graphfs_mcp import features as FT  # noqa: E402
from scp_graphfs_mcp import phase2 as P  # noqa: E402
from scp_graphfs_mcp.complexes import in_any_complex  # noqa: E402
from scp_graphfs_mcp.datasets import load_leduc2022, load_petrosius2023, load_specht2021  # noqa: E402
from scp_graphfs_mcp.ids import group_accessions  # noqa: E402
from scp_graphfs_mcp.imc import imc, permuted_features  # noqa: E402
from scp_graphfs_mcp.priors import build_prior  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [100, 101, 102]
TARGETS = [("petrosius2023", load_petrosius2023, [0, 30]), ("leduc2022", load_leduc2022, [200, 30]),
           ("specht2021", load_specht2021, [200, 30])]


def blocks_for(name, names):
    b = {"go": FT.go_block(names), "hpa": FT.hpa_block(names), "kw": FT.uniprot_keywords_block(names),
         "phys": FT.physical_block(names),
         "spec_cp": FT.spectral_block(build_prior("complexportal", names), names),
         "spec_string": FT.spectral_block(build_prior("string", names), names),
         "corpus": FT.corpus_loadings_block(names, (name,))}
    b["curated_all"] = np.hstack([b[k] for k in ["go", "hpa", "kw", "phys", "spec_cp", "spec_string"]])
    b["all"] = np.hstack([b["curated_all"], b["corpus"]])
    return b


def main():
    rows = []
    t0 = time.time()
    for tname, loader, regimes in TARGETS:
        full = loader()
        names = list(full.var_names)
        in_cx = np.array([in_any_complex(group_accessions(f)) for f in names])
        B = blocks_for(tname, names)
        B["null_curated_all_0"] = permuted_features(B["curated_all"], 0)
        B["null_curated_all_1"] = permuted_features(B["curated_all"], 1)
        B["null_all_0"] = permuted_features(B["all"], 0)
        B["nofeat"] = np.zeros((len(names), 1))
        ct = full.obs["cell_type"].values
        types = sorted(set(ct))
        for n_cells in regimes:
            for kind in ["MCAR", "MNAR"]:
                for seed in SEEDS:
                    if n_cells:
                        rng = np.random.default_rng(seed)
                        idx = np.sort(np.concatenate([rng.choice(np.where(ct == c)[0], n_cells // len(types), replace=False)
                                                      for c in types]))
                    else:
                        idx = np.arange(full.n_obs)
                    X = np.asarray(full.X, float)[idx]
                    eligible = (~np.isnan(X)).mean(0) >= 0.5
                    mask = make_mask(X, eligible, kind, seed)
                    Xm = X.copy()
                    Xm[mask] = np.nan
                    truth = X[mask]
                    _, cols = np.nonzero(mask)
                    sel = in_cx[cols]

                    def score(method, filled):
                        e = filled[mask] - truth
                        rows.append({"target": tname, "n_cells": int(len(idx)), "mask": kind, "seed": seed,
                                     "method": method, "rmse_all": float(np.sqrt(np.mean(e ** 2))),
                                     "rmse_in_complex": float(np.sqrt(np.mean(e[sel] ** 2)))})

                    score("knn", P._fill(Xm, P.loo_knn(Xm)))
                    score("lowrank", P.grmf(Xm, None, names, lam_g=0.0))
                    for bname, F in B.items():
                        score(f"imc_{bname}", imc(Xm, F))
                    print(f"[{time.strftime('%H:%M:%S')}] {tname} n={len(idx)} {kind} {seed} ({time.time() - t0:.0f}s)", flush=True)
    out = ROOT / "results" / "phase5" / "dev"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev_imc.json").write_text(json.dumps({"seeds": SEEDS, "rows": rows}, indent=1) + "\n")
    import pandas as pd

    df = pd.DataFrame(rows)
    print(df.groupby(["target", "n_cells", "mask", "method"])["rmse_all"].mean().unstack("method").round(4).T.to_string())


if __name__ == "__main__":
    main()
