# Signal — Slack Claim Verification Agent

Monitors one Slack channel for status/decision claims ("we deployed X",
"we finished Y") and checks them against recent Slack context plus a
GitHub/deployment data source, retrieved over a real MCP (Model Context
Protocol) connection. The underlying repo/deployment data is seeded for
this sandbox demo, but the connection itself is a genuine MCP server and
client talking the actual protocol, not a same-process function call. If
Signal finds a contradiction or can't confirm the claim, it posts an
evidence-based intervention card in the thread. If the claim checks out,
it stays silent.

## What's new since the first version

- **Real Slack permalinks in evidence citations** -- evidence now links directly
  to the source message instead of just quoting it, so you don't have to
  remember what to search for later (this was a specifically documented,
  heavily-cited Slack complaint).
- **Cooldown to prevent notification spam** -- Signal won't re-flag the same
  topic within 30 minutes, directly addressing notification fatigue, the
  single most-cited Slack complaint by volume.
- **"Verify with Signal" manual message shortcut** -- right-click ANY message
  to force a check on demand, including Slack AI/Slackbot output if your
  workspace has it. Slack's own help docs currently tell users to manually
  ask Slackbot again or provide more specific sources when they suspect a
  hallucination -- this shortcut is the automated version of that.

### Extra setup step for the shortcut

1. Go to your app at api.slack.com/apps -> your app -> **Interactivity & Shortcuts**.
2. Toggle **Interactivity** on (Socket Mode means you don't need a Request URL).
3. Scroll to **Shortcuts** -> **Create New Shortcut** -> choose **On messages**.
4. Name it "Verify with Signal", set the **Callback ID** to exactly `verify_message`
   (must match what's in app.py), add a short description, save.
5. Reinstall the app to your workspace if prompted (Slack sometimes requires this
   after adding a shortcut).
6. In Slack, hover any message -> click the "More actions" (•••) icon -> you
   should see "Verify with Signal" in the list.

## Setup

1. Create a virtual environment (recommended):
   ```
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.template` to `.env` and fill in your real tokens:
   ```
   cp .env.template .env
   ```
   Then edit `.env` with:
   - `SLACK_APP_TOKEN` (starts with `xapp-`, from Socket Mode settings)
   - `SLACK_BOT_TOKEN` (starts with `xoxb-`, from OAuth & Permissions)
   - `GROQ_API_KEY` (from console.groq.com)
   - `TARGET_CHANNEL` (the channel name, no `#`, that you invited the bot to)

4. Run it:
   ```
   python app.py
   ```
   You should see: `[app] Signal is running. Listening for messages...`

## Testing it

Post messages in your target channel and watch the terminal output.

**Should trigger a card** (matches the seeded mock evidence served over the real MCP connection in `mcp_server/mock_data.py`):
> "We deployed payments yesterday, all good now."

Expected: agent finds the mocked rollback + failing check + open PR events,
posts a card showing the mismatch with Medium/Low confidence.

**Should stay silent** (small talk, no claim):
> "anyone free for a quick call later?"

**Should stay silent** (claim with no matching/contradicting evidence):
> "We deployed the notifications service, it's live now."

Expected: this matches evt-005 (deployment_success, no incidents) so the
judge should return SUPPORTS and the agent won't post anything.

If claims that should trigger don't, or claims that should stay quiet
fire anyway, that's the thing to fix before recording your demo — check
the terminal logs, they print the classification and verdict for every
message so you can see exactly where it went wrong.

## What's real vs mocked here

- Slack Bolt + Socket Mode: real, connects to your actual sandbox.
- Claim classification + LLM-as-judge: real Groq calls (llama-3.1-8b-instant).
- RTS API: real, via assistant.search.context -- but only activates when
  the bot is @-mentioned (Slack platform constraint, see Part 6 of
  SETUP_GUIDE.md). Passive monitoring falls back to Slack history.
- MCP connection: real. `mcp_server/server.py` is a genuine MCP server
  (built on the official MCP Python SDK) and `mcp_client.py` connects to
  it as a real MCP client over stdio, using the actual protocol. This was
  tested directly during development, not assumed to work.
- GitHub/deployment data behind that MCP server: mocked, in
  `mcp_server/mock_data.py`, standing in for a live GitHub/deployment
  pipeline connection. Say this plainly in your submission -- the MCP
  integration itself is real and protocol-compliant, only the data behind
  it is seeded for this sandbox demo.
