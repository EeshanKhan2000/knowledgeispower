# S1 variant_to_complexes: merge-gate transcript

- Claude Code version: 2.1.308 (output of `claude --version`)
- MCP server name: `scp-graphfs-s1`
- Model: Sonnet 5.5 (`claude-sonnet-5-5`)
- Branch: `contrib/eeshan-s1`

Notes on what was truncated (per docs/ONBOARDING.md: "Trimming long JSON with `…` is fine if you say so"):
- `dataset_proteins` (2813 feature ids) is shortened below. The full list was passed in the call.
- The MCP result is shortened below. Everything shown is verbatim; omitted parts are marked `… truncated …`.

## User prompt (verbatim)

```text
We are completing only the S1 Variant→complex merge-gate transcript.

The implementation and contributor tests already exist locally on branch contrib/eeshan-s1. Do not reset, replace, or modify variant_bridge.py or the tests.

Use the scp-graphfs-s1 MCP tool variant_to_complexes. Read only the protein feature identifiers (var_names) from data/datasets/petrosius2023_aml_sc.h5ad; do not inspect or transmit the expression matrix or cell-level data. Pass the complete feature identifiers as dataset_proteins.

Answer this exact question:

“A patient has PSMB5:c.100A>G. Which protein machines are affected, and which of their partner subunits are measured in data/datasets/petrosius2023_aml_sc.h5ad?”

Base the answer only on the MCP result. After answering, create contrib/variant_bridge/TRANSCRIPT.md containing:
- Claude Code version and MCP server name
- the user prompt verbatim
- the MCP tool name and arguments
- the MCP result
- Claude’s final answer

Do not invent or reconstruct missing output. Preserve tool data verbatim; long arrays or JSON may be shortened with an explicit “… truncated …” marker, as permitted by docs/ONBOARDING.md.
```

## MCP tool call

Tool: `mcp__scp-graphfs-s1__variant_to_complexes` (server `scp-graphfs-s1`, tool `variant_to_complexes`)

Arguments:

```json
{
  "query": "PSMB5:c.100A>G",
  "dataset_proteins": [
    "A0A024R1R8;Q9Y2S6",
    "A0A075B6H7;A0A0C4DH55;P01624",
    "A0A075B6P5;A0A075B6S2;A0A075B6S6;A0A087WW87;A0A0A0MRZ7;A2NJV5;P01614;P01615;P06310",
    "… truncated … (2813 feature ids in total, read from var_names of data/datasets/petrosius2023_aml_sc.h5ad; the complete list was passed in the call) …",
    "Q9Y6X2",
    "Q9Y6Y8"
  ]
}
```

`sources` was not set (tool default: `["corum", "complexportal"]`).

## MCP result

Header fields (verbatim):

```json
{
 "query": "PSMB5:c.100A>G",
 "input_type": "hgvs",
 "resolved_gene": {
  "symbol": "PSMB5",
  "how": "hgvs_gene"
 },
 "uniprot": [
  "P28074"
 ],
 "complexes": [ … 17 complexes, see below … ],
 "warnings": []
}
```

### First complex, in full (verbatim)

```json
  {
   "complex_id": "CPX-5993",
   "source": "complexportal",
   "name": "26S proteasome complex",
   "members": [
    "O00231", "O00232", "O00487", "O14818", "O43242", "P17980", "P20618", "P25786", "P25787", "P25788",
    "P25789", "P28066", "P28070", "P28072", "P28074", "P35998", "P43686", "P48556", "P49720", "P49721",
    "P51665", "P55036", "P60896", "P60900", "P62191", "P62195", "P62333", "Q13200", "Q15008", "Q16186",
    "Q99436", "Q99460", "Q9UNM6"
   ],
   "partners": [
    { "uniprot": "O00231", "symbols": ["PSMD11"], "in_dataset": true },
    { "uniprot": "O00232", "symbols": ["PSMD12"], "in_dataset": true },
    { "uniprot": "O00487", "symbols": ["PSMD14"], "in_dataset": true },
    { "uniprot": "O14818", "symbols": ["PSMA7"], "in_dataset": true },
    { "uniprot": "O43242", "symbols": ["PSMD3"], "in_dataset": true },
    { "uniprot": "P17980", "symbols": ["PSMC3"], "in_dataset": true },
    { "uniprot": "P20618", "symbols": ["PSMB1"], "in_dataset": true },
    { "uniprot": "P25786", "symbols": ["PSMA1"], "in_dataset": true },
    { "uniprot": "P25787", "symbols": ["PSMA2"], "in_dataset": true },
    { "uniprot": "P25788", "symbols": ["PSMA3"], "in_dataset": true },
    { "uniprot": "P25789", "symbols": ["PSMA4"], "in_dataset": true },
    { "uniprot": "P28066", "symbols": ["PSMA5"], "in_dataset": true },
    { "uniprot": "P28070", "symbols": ["PSMB4"], "in_dataset": true },
    { "uniprot": "P28072", "symbols": ["PSMB6"], "in_dataset": true },
    { "uniprot": "P35998", "symbols": ["PSMC2"], "in_dataset": true },
    { "uniprot": "P43686", "symbols": ["PSMC4"], "in_dataset": true },
    { "uniprot": "P48556", "symbols": ["PSMD8"], "in_dataset": true },
    { "uniprot": "P49720", "symbols": ["PSMB3"], "in_dataset": false },
    { "uniprot": "P49721", "symbols": ["PSMB2"], "in_dataset": true },
    { "uniprot": "P51665", "symbols": ["PSMD7"], "in_dataset": true },
    { "uniprot": "P55036", "symbols": ["PSMD4"], "in_dataset": true },
    { "uniprot": "P60896", "symbols": ["SEM1"], "in_dataset": false },
    { "uniprot": "P60900", "symbols": ["PSMA6"], "in_dataset": true },
    { "uniprot": "P62191", "symbols": ["PSMC1"], "in_dataset": true },
    { "uniprot": "P62195", "symbols": ["PSMC5"], "in_dataset": true },
    { "uniprot": "P62333", "symbols": ["PSMC6"], "in_dataset": true },
    { "uniprot": "Q13200", "symbols": ["PSMD2"], "in_dataset": true },
    { "uniprot": "Q15008", "symbols": ["PSMD6"], "in_dataset": true },
    { "uniprot": "Q16186", "symbols": ["ADRM1"], "in_dataset": true },
    { "uniprot": "Q99436", "symbols": ["PSMB7"], "in_dataset": true },
    { "uniprot": "Q99460", "symbols": ["PSMD1"], "in_dataset": true },
    { "uniprot": "Q9UNM6", "symbols": ["PSMD13"], "in_dataset": true }
   ]
  }
```

(Formatting note for this block only: the tool returned one array element per line; `members` and `partners` entries are compacted onto fewer lines here. Values are unchanged.)

### Remaining 16 complexes (verbatim `complex_id`, `source`, `name`; `partners` truncated)

For each complex below, `members` and the full `partners` list were returned by the tool. `partners` is shortened to the entries with `"in_dataset": false`; all other partner entries had `"in_dataset": true`. … truncated …

| complex_id | source | name | partners with `"in_dataset": false` (uniprot / symbols) |
|---|---|---|---|
| CPX-8806 | complexportal | 20S proteasome complex | P49720 / PSMB3 |
| CPX-8841 | complexportal | PA200-20S single-capped proteasome | P49720 / PSMB3; Q14997 / PSME4 |
| CPX-8842 | complexportal | PA28-alphabeta double-capped 20S proteasome complex | P49720 / PSMB3 |
| CPX-9001 | complexportal | PA28-gamma single-capped 20S proteasome complex | P49720 / PSMB3; P61289 / PSME3 |
| CPX-9002 | complexportal | PA28-alphabeta single-capped 20S proteasome complex | P49720 / PSMB3 |
| CPX-9021 | complexportal | 20S spermatoproteasome complex | P49720 / PSMB3; Q8TAA3 / PSMA8 |
| CPX-9022 | complexportal | PA28-gamma double-capped 20S proteasome complex | P49720 / PSMB3; P61289 / PSME3 |
| CPX-9063 | complexportal | PA200-20S-PA200 double-capped proteasome complex | P49720 / PSMB3; Q14997 / PSME4 |
| CPX-9082 | complexportal | 19S-20S-PA28-alphabeta hybrid proteasome complex | P49720 / PSMB3; P60896 / SEM1 |
| CPX-9085 | complexportal | 19S-20S-PA28-gamma hybrid proteasome complex | P49720 / PSMB3; P60896 / SEM1; P61289 / PSME3 |
| CPX-9086 | complexportal | 30S proteasome complex | P49720 / PSMB3; P60896 / SEM1 |
| CORUM:181 | corum | 26S proteasome | P49720 / PSMB3 |
| CORUM:192 | corum | PA28-20S proteasome | P49720 / PSMB3 |
| CORUM:193 | corum | PA700-20S-PA28 complex | P49720 / PSMB3 |
| CORUM:194 | corum | PA28gamma-20S proteasome | P49720 / PSMB3; P61289 / PSME3 |
| CORUM:8850 | corum | 20S proteasome | P49720 / PSMB3 |

## Claude's final answer

**Resolution.** The tool parsed `PSMB5:c.100A>G` as an HGVS-style variant, resolved it to gene PSMB5 (UniProt P28074), and found it in 17 curated complexes (12 from Complex Portal, 5 from CORUM). No warnings were returned. The tool maps the variant to its gene only. It does not report any effect of the variant on the protein.

**Protein machines (complexes) containing PSMB5**

- Complex Portal: 26S proteasome (CPX-5993), 20S proteasome (CPX-8806), PA200-20S single-capped proteasome (CPX-8841), PA28-alphabeta double-capped 20S proteasome (CPX-8842), PA28-gamma single-capped 20S proteasome (CPX-9001), PA28-alphabeta single-capped 20S proteasome (CPX-9002), 20S spermatoproteasome (CPX-9021), PA28-gamma double-capped 20S proteasome (CPX-9022), PA200-20S-PA200 double-capped proteasome (CPX-9063), 19S-20S-PA28-alphabeta hybrid proteasome (CPX-9082), 19S-20S-PA28-gamma hybrid proteasome (CPX-9085), 30S proteasome (CPX-9086).
- CORUM: 26S proteasome (CORUM:181), PA28-20S proteasome (CORUM:192), PA700-20S-PA28 complex (CORUM:193), PA28gamma-20S proteasome (CORUM:194), 20S proteasome (CORUM:8850).

**Partner subunits measured in petrosius2023_aml_sc.h5ad.** In every one of these complexes, nearly all partner subunits are flagged `in_dataset: true`. For example, the 26S proteasome (CPX-5993) lists 32 partners, of which 30 are measured: the PSMA1-7 alpha subunits, PSMB1, PSMB2, PSMB4, PSMB6 and PSMB7, the PSMC1-6 subset PSMC1, PSMC2, PSMC3, PSMC4, PSMC5 and PSMC6, PSMD1, PSMD2, PSMD3, PSMD4, PSMD6, PSMD7, PSMD8, PSMD11, PSMD12, PSMD13 and PSMD14, and ADRM1. The extra partners in the other complexes that are also measured are PSME1 and PSME2 (PA28-alphabeta complexes), and PSMD5, PSMD9 and PSMD10 (CORUM:193).

**Partner subunits not measured (`in_dataset: false`)**

- PSMB3 (P49720): in all 17 complexes.
- SEM1 (P60896): in CPX-5993, CPX-9082, CPX-9085, CPX-9086.
- PSME3 (P61289): in CPX-9001, CPX-9022, CPX-9085, CORUM:194.
- PSME4 (Q14997): in CPX-8841, CPX-9063.
- PSMA8 (Q8TAA3): in CPX-9021.

**Caveats.** The `in_dataset` flag is the tool's match against the supplied feature ids, which are the 2813 `var_names` of the dataset (some of which are protein groups such as `P1;P2`). The tool result does not say whether PSMB5 itself (the queried protein) is measured, so I make no claim about that. This answer rests only on the MCP result.
