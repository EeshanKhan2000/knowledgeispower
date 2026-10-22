"""Monarch KG gene -> phenotype and gene -> disease associations (human genes only).

Raw files (``data/cache/reps/monarch/``, Monarch KG ``latest/tsv/all_associations/``):

* ``gene_to_phenotypic_feature_association.all.tsv.gz``: used by ``block`` (phenotype term sets,
  mostly HPO ``HP:`` terms).
* ``causal_gene_to_disease_association.all.tsv.gz`` and
  ``correlated_gene_to_disease_association.all.tsv.gz``: their union is used by ``disease_block``
  (MONDO disease term sets).

Rows are kept when ``subject_taxon == NCBITaxon:9606``, the subject is an ``HGNC:`` gene and
``negated`` is not true. HGNC IDs are mapped to UniProt via the HGNC snapshot (``uniprot_ids``).
Terms are used as given; no ontology ancestor propagation is done (no HPO/MONDO ontology file is
downloaded), so related-but-different terms count as unrelated.
"""

from __future__ import annotations

import csv
import gzip
import json
from functools import lru_cache

import numpy as np

from ..features import _accs, _svd_block
from ._kbutil import cache_fresh, hgnc_to_uniprot, read_meta, source_dir, write_meta

NAME = "monarch"
BASE = "https://data.monarchinitiative.org/monarch-kg/latest/tsv/all_associations/"
PHENO_FILE = "gene_to_phenotypic_feature_association.all.tsv.gz"
DISEASE_FILES = ("causal_gene_to_disease_association.all.tsv.gz",
                 "correlated_gene_to_disease_association.all.tsv.gz")
DIR = source_dir(NAME)
RAWS = [DIR / PHENO_FILE] + [DIR / f for f in DISEASE_FILES]
SETS = DIR / "derived_human_term_sets.json"
META = DIR / "derived_meta.json"


def _read(path) -> tuple[dict[str, set[str]], int]:
    h2u = hgnc_to_uniprot()
    idx: dict[str, set[str]] = {}
    n = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if r["subject_taxon"] != "NCBITaxon:9606" or not r["subject"].startswith("HGNC:"):
                continue
            if r.get("negated", "").strip().lower() in ("true", "1"):
                continue
            n += 1
            for acc in h2u.get(r["subject"], ()):
                idx.setdefault(acc, set()).add(r["object"])
    return idx, n


def _build() -> None:
    pheno, n_p = _read(RAWS[0])
    disease: dict[str, set[str]] = {}
    n_d = 0
    for p in RAWS[1:]:
        d, n = _read(p)
        n_d += n
        for k, v in d.items():
            disease.setdefault(k, set()).update(v)
    SETS.write_text(json.dumps({"phenotype": {k: sorted(v) for k, v in pheno.items()},
                                "disease": {k: sorted(v) for k, v in disease.items()}}))
    write_meta(META, RAWS, urls={p.name: BASE + p.name for p in RAWS}, n_human_pheno_rows=n_p,
               n_human_disease_rows=n_d, n_acc_pheno=len(pheno), n_acc_disease=len(disease))


@lru_cache(maxsize=1)
def _sets() -> dict[str, dict[str, set[str]]]:
    if not (SETS.exists() and cache_fresh(META, RAWS)):
        _build()
    raw = json.loads(SETS.read_text())
    return {k: {a: set(t) for a, t in d.items()} for k, d in raw.items()}


def provenance() -> dict:
    _sets()
    m = read_meta(META)
    return {"source": "Monarch KG", "urls": m["urls"], "raw": m["raw"]}


def block(var_names, d: int = 24) -> np.ndarray:
    """SVD embedding of phenotype-term sets (terms with >= 5 proteins among var_names)."""
    idx = _sets()["phenotype"]
    return _svd_block([idx.get(a, set()) for a in _accs(var_names)], vocab_min=5, d=d)


def disease_block(var_names, d: int = 16) -> np.ndarray:
    """SVD embedding of disease-term sets (causal + correlated; terms with >= 2 proteins among var_names,
    because most diseases have very few associated genes)."""
    idx = _sets()["disease"]
    return _svd_block([idx.get(a, set()) for a in _accs(var_names)], vocab_min=2, d=d)
