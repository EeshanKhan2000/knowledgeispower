#!/usr/bin/env bash
# Download the protein-feature sources used by scp_graphfs_mcp.features (Amendment 5) into data/cache/features/.
# Checksums of the snapshots used are in data/PROVENANCE.md ("current" releases may move on).
set -euo pipefail
cd "$(dirname "$0")/../data/cache" && mkdir -p features && cd features
curl -sS -L -O https://current.geneontology.org/annotations/goa_human.gaf.gz
curl -sS -L -O https://www.proteinatlas.org/download/proteinatlas.tsv.zip
curl -sS -L -O https://pax-db.org/downloads/latest/datasets/9606/9606-WHOLE_ORGANISM-integrated.txt
curl -sS -L -O https://stringdb-downloads.org/download/protein.physical.links.v12.5/9606.protein.physical.links.v12.5.txt.gz
curl -sS -L -o uniprot_human.tsv "https://rest.uniprot.org/uniprotkb/stream?query=organism_id:9606+AND+reviewed:true&fields=accession,length,mass,cc_subcellular_location,keyword&format=tsv"
sha256sum *
