# GitHub Copilot CLI — MCP Client Recipe

## Overview

This recipe connects GitHub Copilot CLI to the `scp-graphfs-mcp` server using the STDIO transport and demonstrates a real single-cell proteomics workflow.

**Tested environment**
- OS: Windows
- Python: 3.12.4
- GitHub Copilot CLI: 1.0.102
- MCP server: `scp-graphfs-mcp` 0.1.0
- Client authentication: GitHub Copilot Student

## 1. Install the repository

```powershell
git clone https://github.com/xX-its-amit-Xx/knowledgeispower.git
cd knowledgeispower
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Verify the installation:

```powershell
.\.venv\Scripts\python.exe scripts\mcp_smoke.py
```

Expected: Six MCP tools are discovered.

## 2. Start GitHub Copilot CLI

Install GitHub Copilot CLI using the official GitHub installation instructions:

https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli

From the repository directory:

```powershell
copilot
```

Sign in using `/login`, then open `/mcp`.

## 3. Configure the MCP server

Choose **Add MCP server** and enter:

| Setting | Value |
|---|---|
| Name | `scp-graphfs` |
| Transport | STDIO |
| Command | `"<REPO_PATH>\.venv\Scripts\scp-graphfs-mcp.exe"` |
| Environment variables | Empty |
| Tools | `*` |
| Defer tools | Auto |

Replace `<REPO_PATH>` with the absolute path to your repository.

The CLI starts the MCP server automatically using the configured command. No separate terminal process is required.

Verify the connection in `/mcp` → `scp-graphfs` → **Details**.

Expected status: `connected`.

Expected tools:
- `get_complexes`
- `explain_protein`
- `build_prior`
- `propagate_scores`
- `impute_with_prior`
- `select_panel`

## 4. Reproduction prompt

Run this question in Copilot CLI from the repository directory:

> Which subunits of the 26S proteasome are measured in data/datasets/petrosius2023_aml_sc.h5ad, and how many of their missing values can be filled from partners?

Ask the agent to use the `scp-graphfs` MCP tools and report actual tool arguments and responses.

## 5. Real session — 22 October 2026

**Client:** GitHub Copilot CLI 1.0.102

**Dataset:** `data/datasets/petrosius2023_aml_sc.h5ad`

### Dataset verification

The agent verified the dataset existed:

```text
exists: true
length_bytes: 2588204
```

### MCP call — get_complexes

Arguments:

```json
{
  "id": "PSMB5",
  "sources": ["complexportal"]
}
```

The agent reported that Complex Portal returned `CPX-5993`, the 26S proteasome complex, containing 33 subunits.

Dataset inspection identified **31 measured subunits**. The two absent subunits were `PSMB3` and `SEM1`.

### MCP call — impute_with_prior

The agent created a temporary dataset containing the 31 measured 26S proteasome subunits, outside the repository.

Arguments:

```json
{
  "h5ad_path": "<SESSION_FILES>/petrosius2023_aml_sc_26s_subset.h5ad",
  "output_path": "<SESSION_FILES>/petrosius2023_aml_sc_26s_imputed.h5ad",
  "prior": "complexportal"
}
```

The `<SESSION_FILES>` notation above abbreviates the original absolute session paths for portability.

Reported MCP result:

```json
{
  "prior": "complexportal",
  "beta": 0.9895540412067626,
  "n_missing": 638,
  "n_imputed_from_partners": 607,
  "n_imputed_by_knn_fallback": 31
}
```

The complete tool response additionally included the ten proteins with the highest partner-based imputation counts.

### Answer

The 26S proteasome complex contained 33 reported subunits, of which **31 were measured** in the dataset.

In the temporary 26S-only subset:

- Missing values: **638**
- Filled using observed complex partners: **607**
- Filled using kNN fallback: **31**
- Partner-based fill proportion: **95.1%**

These results apply to the 26S-only subset, not a full-dataset imputation.

## 6. Reproducibility notes

- Run Copilot CLI from the repository root so the dataset's relative path resolves correctly.
- Use absolute paths for MCP file arguments.
- Keep temporary imputation outputs outside the repository.
- Do not overwrite the original dataset.
- The result above is a record of one real session; it is not a guarantee that different software versions or dataset revisions produce identical outputs.
- The complete raw MCP response and shell transcript should be preserved separately for acceptance review.

## 7. Verification

The following local checks succeeded:

```text
Offline tests: 19 passed, 27 xfailed
MCP smoke test: 6 tools discovered
Copilot CLI MCP status: connected
```

## 8. Full Experiment Transcript

The complete GitHub Copilot CLI session is available in:

[Copilot CLI Transcript](./copilot_cli_transcript.md)

The transcript contains:

- Dataset inspection and verification
- The exact Python script used to identify the measured 26S proteasome subunits
- Creation of the temporary 26S-only `.h5ad` subset
- Actual MCP `get_complexes` arguments and responses
- Actual MCP `impute_with_prior` arguments and responses
- Failed attempts and subsequent corrections
- Final experiment results

To reproduce the subset preparation, refer to the
"Identify measured 26S subunits" PowerShell command in the transcript.

Replace the original machine-specific paths with paths valid
for your local environment.


### Transcript Privacy and Reproducibility

The accompanying transcript is a redacted copy of a real
GitHub Copilot CLI session.

Machine-specific Windows paths and local usernames have been
replaced with placeholders such as `<USERNAME>` and `<PROJECT_DIR>`.

The scientific results and MCP tool responses have been
preserved. Some commands require replacing these placeholders
with valid local paths before reproduction.

The transcript includes failed attempts and corrections to
document the actual workflow.