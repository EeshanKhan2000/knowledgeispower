# Onboarding (15 minutes)

1. **Read `README.md`** (3 min): the claim and the headline result.
2. **Read `AGENTS.md`** (4 min): invariants and what you may touch. It's the same file your coding
   agent reads.
3. **Install and run the tests** (3 min):
   ```bash
   git clone https://github.com/xX-its-amit-Xx/knowledgeispower && cd knowledgeispower
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   pytest -q -m "not network"
   ```
4. **Run the core benchmark** (under 30 min on a laptop; `--quick` takes about 2 min):
   `python benchmarks/run.py --quick --out /tmp/bench` (writes outside `results/`).
5. **Read 3 glossary entries** in `docs/glossary.json`: *protein complex*, *stoichiometry*, *MNAR*.
6. **Pick a slot** in `docs/SLOTS.md` and tell Amit.

## Network preflight (run this first, so infrastructure fails fast)
```bash
for u in \
  "https://mips.helmholtz-muenchen.de/corum/" \
  "https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/" \
  "https://string-db.org/api/json/version" \
  "https://rest.uniprot.org/uniprotkb/P28074.json" \
  "https://rest.ensembl.org/info/ping?content-type=application/json" \
  "https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD024043" \
  "https://api.crossref.org/works/10.1093/nar/gkac1015" \
  "https://export.arxiv.org/api/query?id_list=2507.08055" \
  "https://api.biorxiv.org/details/biorxiv/2020-01-01/2020-01-02/0" \
  "https://github.com/xX-its-amit-Xx/scp-prep" ; do
  printf "%s  %s\n" "$(curl -sS -o /dev/null -m 20 -w '%{http_code}' "$u" 2>&1 | tail -c 40)" "$u"
done
```
Everything should return `200`. **CORUM may fail TLS verification**: its server omits an
intermediate certificate. `scripts/fetch_data.sh` handles this correctly. You never need to disable
verification, and the snapshot is already committed anyway.

## Connect the MCP server to Claude
Claude Code:
```bash
claude mcp add scp-graphfs -- /ABS/PATH/.venv/bin/scp-graphfs-mcp
# S1 (Eeshan): mount the contrib tool too
claude mcp add scp-graphfs-s1 -- /ABS/PATH/.venv/bin/scp-graphfs-mcp --enable-contrib variant_to_complexes
```
Claude Desktop (`claude_desktop_config.json`):
```json
{"mcpServers": {"scp-graphfs": {"command": "/ABS/PATH/.venv/bin/scp-graphfs-mcp",
                                "args": ["--enable-contrib", "variant_to_complexes"]}}}
```
Quick check without any client: `python scripts/mcp_smoke.py`.

## Recording a transcript (merge gate)
Use a real client session. Copy the prompts, the tool calls (name + arguments) and the tool results
verbatim into your `TRANSCRIPT.md`. Don't edit tool outputs. Trimming long JSON with `…` is fine
if you say so.
