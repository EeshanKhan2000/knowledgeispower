"""Derive the committed STRING edge table from the raw v12.5 downloads (see data/PROVENANCE.md).

Output: data/derived/string_v12.5_9606_uniprot.tsv.gz with columns
``a, b, combined, experimental`` (STRING scores 0-1000, a < b, canonical UniProt
accessions). Kept: edges with combined >= 400 OR experimental >= 400 (a superset
of every threshold used in the benchmark). ENSP -> UniProt via the aliases file
rows with source ``Ensembl_HGNC_uniprot_ids`` (primary accessions; ``UniProt_AC`` also lists secondary accessions and blows the join up ~20x); an ENSP mapping to several accessions yields
one edge per accession pair; duplicate pairs keep the max score.
"""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

import pandas as pd
from scp_prep import check_resources

from scp_graphfs_mcp.ids import canonical_accession

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "cache" / "string"
OUT = ROOT / "data" / "derived" / "string_v12.5_9606_uniprot.tsv.gz"


def main() -> None:
    al = pd.read_csv(RAW / "9606.protein.aliases.v12.5.txt.gz", sep="\t", dtype=str)
    al.columns = ["ensp", "alias", "source"]
    al = al[al["source"] == "Ensembl_HGNC_uniprot_ids"].copy()  # primary Swiss-Prot accessions only
    al["acc"] = al["alias"].map(canonical_accession)
    al = al.dropna(subset=["acc"])[["ensp", "acc"]].drop_duplicates()

    # ~13M rows: stream in chunks so peak RAM stays laptop-scale.
    check_resources(required_bytes=2 * 1024**3, op="STRING subset build")
    chunks = pd.read_csv(
        RAW / "9606.protein.links.detailed.v12.5.txt.gz", sep=" ",
        usecols=["protein1", "protein2", "experimental", "combined_score"],
        dtype={"protein1": "category", "protein2": "category", "experimental": "int16", "combined_score": "int16"},
        chunksize=1_000_000,
    )
    links = pd.concat(
        c[(c["combined_score"] >= 400) | (c["experimental"] >= 400)].astype({"protein1": str, "protein2": str})
        for c in chunks
    )
    m = links.merge(al, left_on="protein1", right_on="ensp").merge(
        al, left_on="protein2", right_on="ensp", suffixes=("_1", "_2"))
    m = m[m["acc_1"] != m["acc_2"]]
    a = m[["acc_1", "acc_2"]].min(axis=1)
    b = m[["acc_1", "acc_2"]].max(axis=1)
    out = (pd.DataFrame({"a": a, "b": b, "combined": m["combined_score"], "experimental": m["experimental"]})
           .groupby(["a", "b"], as_index=False).max())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(OUT, "wb", mtime=0) as fh:  # mtime=0 -> byte-reproducible
        fh.write(out.to_csv(sep="\t", index=False).encode())
    print(f"{len(out)} edges -> {OUT} sha256={hashlib.sha256(OUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
