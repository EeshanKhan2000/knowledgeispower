# Data provenance

Every database snapshot and dataset used by this repo. Downloaded 2026-10-21 (UTC) unless noted.
`scripts/fetch_data.sh` checks these SHA-256 sums against local files and downloads any that are missing. `--refetch` re-downloads every file and compares it to the committed copy. If a "current"
release has moved on, the checksum will differ: that is expected. Record the new release and its
hash in a new row, and leave the old row in place.

| File | Source URL | Release / version | Downloaded | SHA-256 | Committed? |
|---|---|---|---|---|---|
| `data/raw/corum_humanComplexes.txt` | https://mips.helmholtz-muenchen.de/fastapi-corum/public/file/download_current_file?file_id=human&file_format=txt | CORUM "current" human file, server `Last-Modified: 2026-04-14` | 2026-10-21 | `5e40556eb59bb767f3396ba8c080f64c777903ffca9102345fdc35662a2e0282` | yes |
| `data/raw/complexportal_9606.tsv` | https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/9606.tsv | EBI Complex Portal `current/` (latest dated release dir `2026-01-09/`; file `Last-Modified: 2026-01-14`) | 2026-10-21 | `29d3aeec7ede35e8686de3cf73620b5871c3e68d7ca069385153a9b28e80012a` | yes |
| `data/raw/hgnc_complete_set.txt` | https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt | HGNC complete set, `Last-Modified: 2026-10-16` | 2026-10-21 | `12363916be36f8f6f91879b0faade4eeaac973722de7136ec61329b77f2c2f91` | yes |
| `data/cache/string/9606.protein.links.detailed.v12.5.txt.gz` | https://stringdb-downloads.org/download/protein.links.detailed.v12.5/9606.protein.links.detailed.v12.5.txt.gz | STRING v12.5 (API `/api/json/version` → 12.5), `Last-Modified: 2026-08-01` | 2026-10-21 | `2c447172e6440e77d019a19ebfc608b9fa9cac6501461b432868f0b0d359ba51` | no (103 MB). Derived subset committed, see below |
| `data/cache/string/9606.protein.aliases.v12.5.txt.gz` | https://stringdb-downloads.org/download/protein.aliases.v12.5/9606.protein.aliases.v12.5.txt.gz | STRING v12.5 | 2026-10-21 | `b65f730b993ed0c1bd72edf4565d3d425db42861101b29699704810e8f125680` | no (20 MB) |
| `data/datasets/petrosius2023_aml_sc.h5ad` | Built by `xX-its-amit-Xx/scp-benchmark` `cookbook/build_real_dataset.py` @ `252372aec8ab35e106ecb8c80aca8b583d943c2f` from UCLouvain Dataverse `doi:10.14428/DVN/4DSPJM` (scpdata `petrosius2023_AstralAML`, Spectronaut protein-group report) | 215 cells × 2813 protein groups, 40.7% missing, 4 FACS-gated populations of OCI-AML8227 | copied 2026-10-21 | `c871e40ef3fbd61d8c5dc30838d80568a0fefad1a7f0bf949ece4ebbbaf0ec87` | yes |
| `data/datasets/leduc2022_pscope_proteins_norm2.h5ad` | Built by `scripts/rda_extract_leduc.py` + `scripts/build_leduc2022.py` from https://mghp.osn.xsede.org/bir190004-bucket01/ExperimentHub/scpdata/leduc2022_pSCoPE.Rda (raw `.Rda` SHA-256 `805e1248e8a1ccdf9f3aa0be32a05bc837178a18826f56c36de32369cc4be932`, the same hash scp-zoo recorded) | Leduc et al. 2022 nPOP/pSCoPE, QFeatures assay `proteins_norm2` (**pre-imputation**). 1543 cells (Melanoma 768, Monocyte 775) × proteins, 65.9% missing | 2026-10-21 | `42e491cb820ff6de2838b74262496fd1126318f77718aca19196f069cf0e0d1b` | yes |
| `data/datasets/specht2021_scope2_proteins_from_peptides.h5ad` | Built by `scripts/rda_extract_specht.py` + `scripts/build_specht2021.py` from https://mghp.osn.xsede.org/bir190004-bucket01/ExperimentHub/scpdata/specht2019v3.Rda (raw SHA-256 `db6179e83fb4afca4f00241c2511b5c217b369bcaf23cc97a12de8b335d0e87f`) | SCoPE2 (Specht et al. 2021) `peptides` assay (unimputed), median-aggregated to proteins; 1490 cells (Macrophage 1096, Monocyte 394) × 3042 proteins, 79.5% missing. The scpdata `proteins` assay is imputed and is **not** used. | 2026-10-21 | `380ec58a28148c1316cd1158801313abc7251ce3d6da2e201f88a1ba63428744` | yes |
| `data/raw/humap3_complexes.csv` | https://humap3.proteincomplexes.org/static/downloads/humap3/hu.MAP3.0_complexes_wConfidenceScores_total15326_wGenenames_20240922.csv | hu.MAP 3.0 **predicted** complexes (15,326; ComplexConfidence 1 = highest), release file dated 2024-09-22 | 2026-10-21 | `22a545ce45ced9a57a15f3bff75beaf53cf7e254d8d68635668e2c968bf46739` | yes |
| `data/cache/corpus/schoof2021.npz` (via `scripts/rda_extract_assay.py` + `scripts/build_corpus.py`) | https://mghp.osn.xsede.org/bir190004-bucket01/ExperimentHub/scpdata/schoof2021.Rda | scpdata EH7085, assay `proteins` (unimputed), single cells only; raw `.Rda` SHA-256 `a70f4d74bdba43efb72a4e903b6b3daa7be6d30560c9ec62e9681eb3a4c75d0e` | 2026-10-21 | (cache, rebuildable) | no |
| `data/cache/corpus/woo2022.npz` (same scripts) | https://mghp.osn.xsede.org/bir190004-bucket01/ExperimentHub/scpdata/woo2022_macrophage.Rda | scpdata EH8303, assay `proteins_LFQ` (0 = missing); raw `.Rda` SHA-256 `ba613f5ad4e333a2f021c21935e28555aae5b8530f74f3963dc41a96961d3a3e` | 2026-10-21 | (cache, rebuildable) | no |

## Notes

- **CORUM TLS:** `mips.helmholtz-muenchen.de` serves its leaf certificate without the intermediate
  (`GEANT TLS RSA 1`, issued by `HARICA TLS RSA Root CA 2021`). `scripts/fetch_data.sh` downloads that
  intermediate from the URL in the leaf certificate's Authority Information Access field
  (`http://crt.harica.gr/HARICA-GEANT-TLS-R1.cer`) and adds it to the CA bundle. TLS verification
  is never disabled.
- **Licences:** each source has its own terms. Check them before redistributing: CORUM
  (https://mips.helmholtz-muenchen.de/corum/), Complex Portal (CC0 per EBI), STRING (CC BY 4.0),
  HGNC (freely available), and the Petrosius 2023 data (Dataverse record terms). These were
  **not verified** by fetching the licence pages at snapshot time.
- **Complex Portal is curated only:** `complextab/9606.tsv` holds the 2498 manually curated human complexes (all `CPX-` with curator-assigned ECO evidence). The hu.MAP 3.0 machine-predicted complexes are distributed separately as `9606_predicted.tsv`, which is **not** used.
- **The dataset ships without `layers['raw']`.** The loader in `scp_graphfs_mcp.datasets` adds it
  as `2**X`, which follows the convention exactly but is not an independent raw export.

## Derived files

| File | Built by | From | SHA-256 |
|---|---|---|---|
| `data/derived/string_v12.5_9606_uniprot.tsv.gz` | `scripts/build_string_subset.py` | STRING v12.5 links (detailed) + aliases (`Ensembl_HGNC_uniprot_ids` rows), edges with combined ≥ 400 or experimental ≥ 400; 1,050,464 UniProt pairs | `a933a71db0671f11d8ef86e0084ccfb3f375920a834e7cd3f3588914b47f1a78` |
