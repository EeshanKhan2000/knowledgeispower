#!/usr/bin/env bash
# Re-download every snapshot listed in data/PROVENANCE.md and verify SHA-256.
# Committed files (data/raw, data/datasets) are only needed if you deleted them;
# the STRING raw files (data/cache/string) are needed to rebuild data/derived/string_*.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw data/cache/string
tmp=$(mktemp -d)

# CORUM serves an incomplete chain; complete it from the leaf's AIA URL (verification stays on).
base_ca=${SSL_CERT_FILE:-${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}}
curl -sS -m 60 -o "$tmp/inter.der" http://crt.harica.gr/HARICA-GEANT-TLS-R1.cer
openssl x509 -inform DER -in "$tmp/inter.der" -out "$tmp/inter.pem"
cat "$base_ca" "$tmp/inter.pem" > "$tmp/ca.pem"

fetch() { # url dest [curl args...]
  local url=$1 dest=$2; shift 2
  [ -s "$dest" ] && { echo "have $dest"; return; }
  echo "fetch $dest"; curl -sS -m 1800 -L "$@" -o "$dest" "$url"
}
fetch "https://mips.helmholtz-muenchen.de/fastapi-corum/public/file/download_current_file?file_id=human&file_format=txt" data/raw/corum_humanComplexes.txt --cacert "$tmp/ca.pem"
fetch https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/9606.tsv data/raw/complexportal_9606.tsv
fetch https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt data/raw/hgnc_complete_set.txt
fetch https://stringdb-downloads.org/download/protein.links.detailed.v12.5/9606.protein.links.detailed.v12.5.txt.gz data/cache/string/9606.protein.links.detailed.v12.5.txt.gz
fetch https://stringdb-downloads.org/download/protein.aliases.v12.5/9606.protein.aliases.v12.5.txt.gz data/cache/string/9606.protein.aliases.v12.5.txt.gz

# Verify against PROVENANCE.md (first column = path in backticks, SHA in backticks).
grep -oE '^\| `[^`]+` .*`[0-9a-f]{64}`' data/PROVENANCE.md | while read -r line; do
  path=$(echo "$line" | grep -oE '^\| `[^`]+`' | tr -d '|` ')
  want=$(echo "$line" | grep -oE '`[0-9a-f]{64}`' | tr -d '`')
  [ -f "$path" ] || { echo "MISSING $path"; continue; }
  got=$(sha256sum "$path" | cut -d' ' -f1)
  [ "$got" = "$want" ] && echo "OK      $path" || echo "CHANGED $path (release moved on? record it in PROVENANCE.md)"
done
rm -rf "$tmp"
