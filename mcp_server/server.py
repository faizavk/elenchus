"""
Real MCP server for Signal.

This is a genuine Model Context Protocol server -- it speaks the actual
protocol (via the official MCP Python SDK), not a same-process function
call. It exposes one tool, `search_repo_events`, that Signal's app.py
connects to as an MCP client over stdio.

The DATA behind this tool is seeded/mocked (see mock_data.py) standing in
for a live GitHub/deployment pipeline connection. The PROTOCOL is real --
swapping mock_data.py for a live GitHub API call would not require changing
how the client talks to this server at all.

This file is run as a subprocess by the client (evidence.py), not run
directly by you. You don't need to start this manually.
"""

from mcp.server.fastmcp import FastMCP
from mock_data import query_events

mcp = FastMCP("signal-github-connector")


@mcp.tool()
def search_repo_events(keywords: list[str]) -> list[dict]:
    """
    Search repository/deployment activity (commits, PRs, rollbacks, test
    failures) for events matching the given topic keywords.

    Args:
        keywords: Topic keywords extracted from a Slack claim, e.g.
                   ["payments", "checkout"].

    Returns:
        A list of matching events, each with id, type, repo, summary,
        timestamp, and link fields.
    """
    return query_events(keywords)


if __name__ == "__main__":
    mcp.run(transport="stdio")
