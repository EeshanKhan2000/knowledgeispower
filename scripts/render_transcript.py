"""Render a `claude -p --output-format stream-json --verbose` log to markdown, verbatim.

Tool results longer than --max-chars are truncated and marked as such; nothing else is edited.
Usage: python scripts/render_transcript.py session.jsonl --prompt-file p.txt > demo/agent_session.md
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("jsonl")
ap.add_argument("--max-chars", type=int, default=2500)
ap.add_argument("--title", default="Agent session")
a = ap.parse_args()

out = [f"# {a.title}", "",
       "Recorded with `claude -p ... --mcp-config <scp-graphfs-mcp> --output-format stream-json`; only the "
       "scp-graphfs MCP tools were allowed. Rendered by `scripts/render_transcript.py`. Prompts, tool calls "
       "and tool results are verbatim; tool results over "
       f"{a.max_chars} characters are truncated where marked `[… truncated N chars]`.", ""]
for line in open(a.jsonl):
    ev = json.loads(line)
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        out += [f"**Model:** `{ev.get('model')}` · **MCP servers:** "
                f"{', '.join(s['name'] + ' (' + s['status'] + ')' for s in ev.get('mcp_servers', []))}", ""]
    if t not in ("user", "assistant"):
        continue
    content = ev["message"]["content"]
    if isinstance(content, str):
        out += ["## User", "", content, ""]
        continue
    for c in content:
        if c["type"] == "text" and c["text"].strip():
            out += [f"## {'Assistant' if t == 'assistant' else 'User'}", "", c["text"], ""]
        elif c["type"] == "tool_use":
            out += [f"### Tool call: `{c['name']}`", "", "```json", json.dumps(c["input"], indent=1), "```", ""]
        elif c["type"] == "tool_result":
            body = c["content"]
            if isinstance(body, list):
                body = "\n".join(x.get("text", "") for x in body)
            if len(body) > a.max_chars:
                body = body[: a.max_chars] + f"\n[… truncated {len(body) - a.max_chars} chars]"
            out += ["#### Tool result" + (" (error)" if c.get("is_error") else ""), "", "```json", body, "```", ""]
print("\n".join(out))
