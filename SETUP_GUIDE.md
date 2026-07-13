# Signal — Complete Setup & Run Guide

Everything below is free. No paid Slack plan, no credit card, no paid API
tier required anywhere in this guide.

---

## Part 1 — Slack workspace and app (one-time)

If you already did this earlier in the build, skip to Part 2.

1. **Create a free Slack workspace**: go to slack.com/get-started -> "Create
   a new workspace" -> enter email -> confirm code -> name it anything ->
   skip inviting teammates.

2. **Create a Slack app**: go to api.slack.com/apps -> "Create New App" ->
   "From scratch" -> name it (e.g. "Signal") -> pick your new workspace ->
   "Create App".

3. **Enable Socket Mode**: left sidebar -> "Socket Mode" -> toggle on ->
   generate an App-Level Token (name it anything, keep the default
   `connections:write` scope) -> **copy and save this token** (starts with
   `xapp-`). You won't see it again after closing the popup.

4. **Add Bot Token Scopes**: left sidebar -> "OAuth & Permissions" -> scroll
   to "Bot Token Scopes" -> add each of these:
   - `channels:history`
   - `chat:write`
   - `app_mentions:read`
   - `channels:read`

5. **Install the app**: same page, scroll up, click "Install to Workspace"
   -> "Allow" -> **copy and save the Bot User OAuth Token** (starts with
   `xoxb-`) that now appears at the top of the page.

6. **Create a test channel**: in Slack, click "+" next to Channels -> "Create
   a new channel" -> name it `claim-verification` -> public -> Create.

7. **Invite the bot to the channel**: inside the channel, type
   `/invite @Signal` (use whatever name you gave the app) and press enter.
   If it doesn't autocomplete, click the channel name -> "Integrations" ->
   "Add apps" -> find your app -> add it.

## Part 2 — Register the manual "Verify with Signal" shortcut (one-time)

1. Back at api.slack.com/apps -> your app -> "Interactivity & Shortcuts".
2. Toggle "Interactivity" on. You do NOT need a Request URL, Socket Mode
   covers this.
3. Scroll to "Shortcuts" -> "Create New Shortcut" -> choose "On messages".
4. Name: "Verify with Signal". **Callback ID must be exactly**: `verify_message`
   (this has to match app.py exactly, it's already set correctly in the code).
5. Add a short description, click "Create".
6. If Slack prompts you to reinstall the app, do it (OAuth & Permissions ->
   "Install to Workspace" again). This regenerates your Bot Token — if it
   changes, update your `.env` file with the new one.

## Part 3 — Get a free Groq API key (one-time)

1. Go to console.groq.com and sign in (Google account works).
2. Left sidebar -> "API Keys" -> "Create API Key".
3. Copy the key (starts with `gsk_`). Groq's free tier requires no credit
   card and has a much higher daily request quota than Gemini's, which
   matters here since the classifier runs on every message.

## Part 4 — Local setup (one-time)

You need Python 3.10 or newer installed on your machine.

1. Unzip the project folder anywhere, then open a terminal in it.

2. Create a virtual environment (keeps dependencies isolated):
   ```
   python -m venv venv
   ```
   Activate it:
   - Mac/Linux: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`

3. Install dependencies (all free, open-source packages from PyPI):
   ```
   pip install -r requirements.txt
   ```

4. Create your real `.env` file from the template:
   ```
   cp .env.template .env
   ```
   (Windows: `copy .env.template .env`)

5. Open `.env` in any text editor and fill in the four values you saved
   above:
   ```
   SLACK_APP_TOKEN=xapp-...
   SLACK_BOT_TOKEN=xoxb-...
   GROQ_API_KEY=gsk_...
   TARGET_CHANNEL=claim-verification
   ```

## Part 5 — Run it

### Step A: offline test first (recommended, catches most issues fast)

```
python test_offline.py
```

This only needs your `GROQ_API_KEY` to be set. It runs 6 sample messages
through the real classifier, the real MCP server connection, and the real
judge, and tells you if anything disagrees with the expected result. Look
for any line starting with `>>> MISMATCH`. If everything looks clean, move on.

### Step B: connect to live Slack

```
python app.py
```

You should see:
```
[app] Monitoring channel #claim-verification (C0XXXXXXX)
[app] Signal is running. Listening for messages and shortcuts...
```

If you instead see a `WARNING: could not find channel`, double check the
channel name in `.env` matches exactly (no `#`) and that the bot was
actually invited to it (Part 1, step 7).

### Step C: test in Slack

In your `#claim-verification` channel, post:
> We deployed payments yesterday, all good now.

Wait a few seconds (it makes two Gemini calls plus an MCP call, so it's not
instant). You should see a card reply appear in the thread showing a
mismatch, with Medium or Low confidence.

Then post something unrelated:
> anyone free for a call later?

This should get no reply at all. That's correct, not a bug — Signal only
speaks up when something needs flagging.

To test the manual shortcut: hover over any message -> click the "•••"
(more actions) icon -> "Verify with Signal" -> it runs a check on demand
and replies in-thread either way (found an issue, or confirmed no issue).

---

## Part 6 — Optional: enable the real RTS API (Real-Time Search)

This is optional and separate from everything above -- Signal works fully
without it, using Slack conversation history for evidence. RTS adds
richer, workspace-wide search, but ONLY activates when someone @-mentions
the bot directly (e.g. "@Signal we deployed payments yesterday") -- Slack
only issues the required token in that specific case, not for passive
channel monitoring. This is a real Slack platform constraint, not a
limitation in this code.

1. In your Slack app settings -> "Features" -> "Agents & AI Assistants" ->
   toggle it on. This auto-adds an `assistant:write` scope.
2. Go to "OAuth & Permissions" -> add the `search:read.public` scope.
3. Go to "Event Subscriptions" -> under "Subscribe to bot events" -> add
   `app_mention` if it isn't already there.
4. Reinstall the app to your workspace (this is required after adding
   scopes) -> if the Bot Token changes, update your `.env`.
5. Test it by @-mentioning the bot with a claim in your channel, e.g.:
   > @Signal we deployed payments yesterday, all good now.

   Check the terminal output for the line `action_token present -- using
   real RTS API for workspace-wide context.` If you see that, RTS is
   working. If you don't see it, double check steps 1-3 above.

---

## If something doesn't work

Read the terminal output — every step (classification, keywords, MCP
result, verdict) is printed live, so you can see exactly where it
diverged from what you expected. Copy the relevant lines and send them
over rather than just saying "it didn't work."
