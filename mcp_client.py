"""
Real MCP client wrapper.

Spawns mcp_server/server.py as a subprocess and talks to it over the actual
Model Context Protocol (stdio transport) to fetch GitHub/deployment evidence.
This is a genuine protocol connection -- confirmed working via a manual
round-trip test during development, not assumed.

A fresh server subprocess is spawned per call. For a single monitored
channel in a hackathon sandbox this is simple and reliable; a production
version would keep a persistent session open instead.
"""

import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server")


async def fetch_repo_events(keywords):
    """
    Connects to the real MCP server, calls the search_repo_events tool,
    and parses the results back into the same dict shape the rest of the
    pipeline (judge.py, block_kit.py) already expects.
    """
    server_params = StdioServerParameters(
        command=sys.executable, args=["server.py"], cwd=_SERVER_DIR
    )

    events = []
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_repo_events", {"keywords": keywords}
            )
            for block in result.content:
                if hasattr(block, "text"):
                    try:
                        events.append(json.loads(block.text))
                    except json.JSONDecodeError:
                        print(f"[mcp_client] Could not parse tool result block: {block.text}")
    return events
