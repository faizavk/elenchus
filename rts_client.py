"""
Real-Time Search (RTS) API client.

Calls the actual assistant.search.context method. Important, real constraint
(not a bug): Slack only provides a usable action_token when the bot is
@-mentioned in a message, or DM'd -- passive channel monitoring on plain
messages does NOT receive one. So this is a genuine enhancement, not a
replacement for the existing conversations_history-based evidence gathering:

  - If someone writes "@Elenchus we deployed payments yesterday" -- an
    action_token is present, and this module gets called to pull richer,
    workspace-wide context via the real RTS API.
  - If someone just posts "we deployed payments yesterday" with no mention --
    no action_token is available, RTS is skipped, and the existing
    same-channel Slack history (evidence.py) is used instead, exactly as
    before this feature was added.

Requires (Slack-side app configuration, not code):
  - "Agents & AI Assistants" feature enabled in app settings
  - search:read.public scope added
  - app_mention event subscribed under Event Subscriptions
"""


def search_context(client, query, action_token, limit=10):
    """
    Calls the real assistant.search.context Web API method.

    Returns a list of dicts: {content, permalink, channel_id, message_ts,
    is_author_bot} -- or an empty list if the call fails, since RTS is an
    enhancement and its failure should never break the main pipeline.
    """
    try:
        response = client.api_call(
            api_method="assistant.search.context",
            json={
                "query": query,
                "action_token": action_token,
                "content_types": ["messages"],
                "channel_types": ["public_channel", "private_channel"],
                "include_context_messages": True,
                "limit": min(limit, 20),  # API hard cap is 20
            },
        )
    except Exception as e:
        print(f"[rts_client] RTS call failed, continuing without it: {e}")
        return []

    if not response.get("ok"):
        print(f"[rts_client] RTS call returned not-ok: {response.get('error')}")
        return []

    messages = response.get("results", {}).get("messages", [])
    return [
        {
            "content": m.get("content", ""),
            "permalink": m.get("permalink"),
            "channel_id": m.get("channel_id"),
            "message_ts": m.get("message_ts"),
            "is_author_bot": m.get("is_author_bot", False),
        }
        for m in messages
    ]
