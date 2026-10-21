"""Spawn the MCP server over stdio and call each tool once (smoke test / transcript helper)."""
import json, sys
import anyio
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

async def main(calls):
    params = StdioServerParameters(command=sys.executable, args=["-m", "scp_graphfs_mcp.server", *sys.argv[1:]])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            for name, args in calls:
                res = await s.call_tool(name, args)
                print(f"--- {name}({args}) is_error={res.is_error}\n{res.content[0].text[:600]}")

anyio.run(main, [("explain_protein", {"id": "PSMB5"}), ("get_complexes", {"id": "NOTAGENE"})])
