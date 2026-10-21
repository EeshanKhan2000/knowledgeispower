"""MCP server (official MCP Python SDK, low-level API, stdio transport).

Mounts every *core* tool in :data:`scp_graphfs_mcp.registry.TOOLS`, plus the
contrib tools explicitly enabled with ``--enable-contrib name[,name]`` or the
``SCP_GRAPHFS_ENABLE_CONTRIB`` environment variable.

Run::

    scp-graphfs-mcp                                   # core tools only
    scp-graphfs-mcp --enable-contrib variant_to_complexes
"""

from __future__ import annotations

import argparse
import json
import os
import traceback

import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from . import tools as _core_tools  # noqa: F401  (registers core tools)
from .registry import TOOLS, ToolEntry, load_contrib

INSTRUCTIONS = (
    "Curated protein-complex priors (CORUM, EBI Complex Portal) for single-cell proteomics. "
    "Use get_complexes / explain_protein to look up complex membership; build_prior to build a "
    "graph over a protein list; impute_with_prior and select_panel operate on .h5ad files "
    "(cells=obs, proteins=var, X=log2 with NaN for missing). Every result reports its provenance; "
    "do not state complex memberships that a tool did not return."
)


def mounted_tools(enable_contrib: list[str] | None = None) -> dict[str, ToolEntry]:
    enabled = set(enable_contrib or [])
    enabled |= {s.strip() for s in os.environ.get("SCP_GRAPHFS_ENABLE_CONTRIB", "").split(",") if s.strip()}
    if enabled:
        load_contrib()
    return {n: t for n, t in TOOLS.items() if not t.contrib or n in enabled}


def build_server(enable_contrib: list[str] | None = None) -> Server:
    tools = mounted_tools(enable_contrib)

    async def on_list_tools(ctx, params):
        return types.ListToolsResult(
            tools=[
                types.Tool(name=t.name, description=t.description, input_schema=t.input_schema)
                for t in tools.values()
            ]
        )

    async def on_call_tool(ctx, params):
        t = tools.get(params.name)
        if t is None:
            out, err = {"error": {"code": "unknown_tool", "message": params.name}}, True
        else:
            try:
                out = await anyio.to_thread.run_sync(lambda: t.func(**(params.arguments or {})))
                err = isinstance(out, dict) and "error" in out
            except Exception as exc:  # noqa: BLE001 — surface to the agent, never crash the server
                out = {"error": {"code": type(exc).__name__, "message": str(exc),
                                 "trace": traceback.format_exc(limit=3)}}
                err = True
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(out, indent=1, default=str))],
            is_error=err,
        )

    return Server("scp-graphfs-mcp", version="0.1.0", instructions=INSTRUCTIONS,
                  on_list_tools=on_list_tools, on_call_tool=on_call_tool)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="scp-graphfs-mcp")
    ap.add_argument("--enable-contrib", default="", help="comma-separated contrib tool names to mount")
    args = ap.parse_args(argv)
    server = build_server([s for s in args.enable_contrib.split(",") if s])

    async def _run():
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())

    anyio.run(_run)


if __name__ == "__main__":
    main()
