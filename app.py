"""
Signal -- main app.

Two entry points into the same verification pipeline:
  1. Automatic: listens to messages in the target channel, classifies each
     one, and investigates anything that looks like a status/decision claim.
  2. Manual: a "Verify with Signal" message shortcut lets anyone right-click
     ANY message (a coworker's claim, or Slack AI's own summary/answer) and
     force a check on demand. This is the automated version of what Slack's
     own help docs currently tell users to do by hand when they suspect a
     Slackbot/Slack AI response might be hallucinated (ask again, provide
     more specific sources, verify manually).

Pipeline for both paths:
  1. Determine claim_text + keywords (via classifier, or directly from the
     shortcut-selected message).
  2. Gather evidence: Slack history (with permalinks) + mocked GitHub/MCP source.
  3. Judge: SUPPORTS / CONTRADICTS / INSUFFICIENT, with a confidence estimate.
  4. If CONTRADICTS or INSUFFICIENT and not on cooldown for this topic: post
     an intervention card in-thread. Otherwise stay silent.

Run with: python app.py
"""
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- Dummy HTTP Server for Render Free Tier Health Checks ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Elenchus is alive!")

    def log_message(self, format, *args):
        # Mute standard logging to keep Render terminal logs clean
        return

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[HealthCheck] Dummy server listening on port {port}...")
    server.serve_forever()
# ------------------------------------------------------------

import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from claim_classifier import classify_message
from evidence import get_recent_slack_context, get_external_evidence, attach_permalinks, rts_results_to_evidence
from judge import judge_claim
from block_kit import build_intervention_card
from cooldown import is_on_cooldown, mark_flagged
from rts_client import search_context

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
os.environ["GROQ_API_KEY"]  # fail fast at startup if missing, rather than on the first message
TARGET_CHANNEL_NAME = os.environ.get("TARGET_CHANNEL", "claim-verification")

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

_target_channel_id = None


def _resolve_target_channel_id():
    global _target_channel_id
    result = app.client.conversations_list(types="public_channel")
    for ch in result.get("channels", []):
        if ch["name"] == TARGET_CHANNEL_NAME:
            _target_channel_id = ch["id"]
            print(f"[app] Monitoring channel #{TARGET_CHANNEL_NAME} ({_target_channel_id})")
            return
    print(f"[app] WARNING: could not find channel '{TARGET_CHANNEL_NAME}'. "
          f"Make sure it exists and the bot has been invited to it.")


def run_verification_pipeline(client, channel_id, message_ts, claim_text, keywords,
                               respect_cooldown=True, action_token=None):
    """
    Shared pipeline used by both the automatic listener and the manual shortcut.

    action_token, when present (only when the bot was @-mentioned or DM'd --
    see rts_client.py), triggers a real call to the Real-Time Search API for
    richer, workspace-wide context alongside the existing same-channel history.
    """
    if respect_cooldown and keywords and is_on_cooldown(keywords):
        print(f"[app] Topic on cooldown ({keywords}), staying silent to avoid notification fatigue.")
        return None

    slack_context = get_recent_slack_context(client, channel_id, exclude_ts=message_ts)
    external_events = get_external_evidence(keywords)

    rts_results = []
    if action_token:
        print("[app] action_token present -- using real RTS API for workspace-wide context.")
        rts_results = search_context(client, claim_text, action_token)
        # Fold RTS message content into the judge's Slack context too, not just the card.
        slack_context = slack_context + [(r["content"], None) for r in rts_results if r.get("content")]

    verdict_result = judge_claim(claim_text, slack_context, external_events)
    print(f"[app] Verdict: {verdict_result['verdict']} | Confidence: {verdict_result['confidence']}")

    if verdict_result["verdict"] == "SUPPORTS":
        print("[app] Claim supported by evidence -- staying silent.")
        return None

    # Slack history needs a permalink fetched; RTS results already include one.
    slack_context_needing_permalinks = [(t, ts) for t, ts in slack_context if ts is not None]
    slack_evidence_with_links = attach_permalinks(client, channel_id, slack_context_needing_permalinks)
    slack_evidence_with_links += rts_results_to_evidence(rts_results)

    blocks = build_intervention_card(claim_text, verdict_result, external_events, slack_evidence_with_links)

    if keywords:
        mark_flagged(keywords)

    return blocks


@app.event("message")
def handle_message(event, client, say):
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_id = event.get("channel")
    if _target_channel_id and channel_id != _target_channel_id:
        return

    message_text = event.get("text", "")
    message_ts = event.get("ts")

    if not message_text.strip():
        return

    print(f"[app] Received message: {message_text}")

    classification = classify_message(message_text)
    if not classification["is_claim"]:
        print("[app] Not a status/decision claim -- staying silent.")
        return

    claim_text = classification["claim_text"]
    keywords = classification["keywords"]
    print(f"[app] Claim detected: '{claim_text}' | keywords: {keywords}")

    # Real action_token from Slack. Confirmed via live debug output that it
    # appears at the top level of the event payload (event['action_token']),
    # not nested under assistant_thread as Slack's own example JSON suggests --
    # checking both, top-level first, since that's what we've actually seen.
    action_token = event.get("action_token") or (event.get("assistant_thread") or {}).get("action_token")

    blocks = run_verification_pipeline(
        client, channel_id, message_ts, claim_text, keywords,
        respect_cooldown=True, action_token=action_token
    )
    if blocks:
        say(blocks=blocks, thread_ts=message_ts, text="Potential mismatch detected (see card above).")


@app.shortcut("verify_message")
def handle_verify_shortcut(ack, shortcut, client):
    """
    Manual "Verify with Signal" message shortcut. Lets someone force a check
    on any message, including Slack AI/Slackbot output, on demand -- the
    automated version of Slack's own manual hallucination-checking advice.
    """
    ack()

    message = shortcut["message"]
    channel_id = shortcut["channel"]["id"]
    message_ts = message["ts"]
    message_text = message.get("text", "")

    if not message_text.strip():
        return

    print(f"[app] Manual verify requested on: {message_text}")

    # Still run the classifier to extract a clean claim + keywords, but don't
    # gate on is_claim -- the human already decided this is worth checking.
    classification = classify_message(message_text)
    claim_text = classification["claim_text"] or message_text
    keywords = classification["keywords"]

    # Manual requests bypass cooldown -- if someone explicitly asks, answer them.
    blocks = run_verification_pipeline(
        client, channel_id, message_ts, claim_text, keywords, respect_cooldown=False
    )

    if blocks:
        client.chat_postMessage(
            channel=channel_id, thread_ts=message_ts, blocks=blocks,
            text="Verification result (see card above)."
        )
    else:
        client.chat_postMessage(
            channel=channel_id, thread_ts=message_ts,
            text="No contradiction or issue found. This claim appears consistent with available evidence."
        )


if __name__ == "__main__":
    _resolve_target_channel_id()
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    print("[app] Signal is running. Listening for messages and shortcuts...")
    handler.start()

#-----------------------------------------

if __name__ == "__main__":
    _resolve_target_channel_id()
    
    # 1. Connect to Slack (handler.connect() automatically runs in the background)
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.connect()
    print("[app] Signal is running. Listening for messages and shortcuts...", flush=True)

    # 2. Run the dummy server on the MAIN thread so Render detects the port instantly
    port = int(os.environ.get("PORT", 10000))
    print(f"[HealthCheck] Binding to port {port}...", flush=True)
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()