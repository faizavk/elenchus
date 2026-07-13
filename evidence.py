"""
Evidence retrieval.

Two sources, matching the locked architecture:
  1. Slack history in the same channel (stand-in for the Slack RTS API pattern --
     for the hackathon sandbox, conversations_history covers the same need;
     see rts_client.py for the real assistant.search.context attempt).
  2. GitHub/deployment events retrieved over a REAL MCP connection -- see
     mcp_server/server.py and mcp_client.py. The underlying data is mocked,
     the protocol connection is genuine.
"""

import asyncio
from mcp_client import fetch_repo_events


def get_recent_slack_context(client, channel_id, exclude_ts, limit=15):
    """
    Fetch recent messages from the channel to give the judge conversational
    context around the claim (e.g. someone else mentioning a rollback earlier
    in the same thread of conversation).

    Returns a list of (text, ts) tuples -- the ts is kept so evidence citations
    can link back to a real permalink instead of just quoted text.
    """
    try:
        result = client.conversations_history(channel=channel_id, limit=limit)
        messages = result.get("messages", [])
        # Exclude the claim message itself and any bot messages.
        context = [
            (m.get("text", ""), m.get("ts"))
            for m in messages
            if m.get("ts") != exclude_ts and not m.get("bot_id")
        ]
        return context
    except Exception as e:
        print(f"[evidence] Failed to fetch Slack history: {e}")
        return []


def get_external_evidence(keywords):
    """
    Query the real MCP server for events matching the claim's keywords.
    Wraps the async MCP client call in asyncio.run() since the rest of the
    Slack Bolt app is synchronous.
    """
    if not keywords:
        return []
    try:
        return asyncio.run(fetch_repo_events(keywords))
    except Exception as e:
        print(f"[evidence] MCP call failed, returning no external evidence: {e}")
        return []


def attach_permalinks(client, channel_id, slack_context_with_ts):
    """
    Given a list of (message_text, message_ts) tuples, fetch a real Slack
    permalink for each so evidence cards link directly to the source message
    instead of just quoting text the person then has to go search for manually.
    This directly addresses a heavily-documented Slack complaint: users report
    that finding an old message again requires already remembering what to
    search for, which defeats the purpose of search. A clickable permalink
    removes that burden entirely.
    """
    results = []
    for text, ts in slack_context_with_ts:
        try:
            resp = client.chat_getPermalink(channel=channel_id, message_ts=ts)
            link = resp.get("permalink")
        except Exception as e:
            print(f"[evidence] Could not fetch permalink for ts={ts}: {e}")
            link = None
        results.append({"text": text, "permalink": link})
    return results


def rts_results_to_evidence(rts_results):
    """
    RTS API results already include a permalink, so no extra API call is
    needed here -- just reshape into the same {text, permalink} format the
    card builder expects for Slack-native evidence.
    """
    return [
        {"text": r["content"], "permalink": r.get("permalink")}
        for r in rts_results
        if r.get("content")
    ]

