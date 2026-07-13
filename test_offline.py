"""
Offline test harness.

Tests the claim classifier + evidence retrieval + judge pipeline WITHOUT
needing a live Slack connection. Only requires GROQ_API_KEY in your .env.

This now also exercises the REAL MCP server/client connection (evidence.py
spawns mcp_server/server.py and talks to it over the actual protocol), so
if MCP setup is broken, you'll see it fail here too, before touching Slack.

Use this first, before running app.py against live Slack. If something's
wrong with the classifier, judge, or MCP connection, you'll see it here in
seconds instead of debugging it through Slack's UI.

Run with: python test_offline.py
"""

import time
from dotenv import load_dotenv

from claim_classifier import classify_message
from evidence import get_external_evidence
from judge import judge_claim
from block_kit import build_intervention_card

load_dotenv()

# Groq's free tier has a much higher quota than what we hit on Gemini, but a
# small pacing delay is kept as a safety margin against per-minute limits.
SECONDS_BETWEEN_CALLS = 3

# (message, expected_is_claim, expected_verdict_if_claim)
# expected_verdict is None if we don't expect it to even reach the judge.
TEST_CASES = [
    ("We deployed payments yesterday, all good now.", True, "CONTRADICTS"),
    ("We deployed the notifications service, it's live now.", True, "SUPPORTS"),
    ("anyone free for a quick call later?", False, None),
    ("haha that meeting was chaotic", False, None),
    ("We finished migrating to OAuth2 last week.", True, "SUPPORTS"),
    ("I think we should probably look into caching at some point.", False, None),
]


def run_case(message, expected_is_claim, expected_verdict):
    print(f"\n{'='*70}")
    print(f"MESSAGE: {message}")
    print(f"{'='*70}")

    classification = classify_message(message)
    is_claim = classification["is_claim"]
    print(f"  Classified as claim: {is_claim}  (expected: {expected_is_claim})")

    if is_claim != expected_is_claim:
        print(f"  >>> MISMATCH: classifier disagreement, check claim_classifier.py prompt")

    if not is_claim:
        return

    print(f"  Claim text: {classification['claim_text']}")
    print(f"  Keywords: {classification['keywords']}")

    time.sleep(SECONDS_BETWEEN_CALLS)  # stay under free tier rate limit before the judge call

    external_events = get_external_evidence(classification["keywords"])
    print(f"  External evidence found: {len(external_events)} events")

    verdict_result = judge_claim(classification["claim_text"], [], external_events)
    print(f"  Verdict: {verdict_result['verdict']}  (expected: {expected_verdict})")
    print(f"  Confidence: {verdict_result['confidence']}")
    print(f"  Explanation: {verdict_result['explanation']}")

    if expected_verdict and verdict_result["verdict"] != expected_verdict:
        print(f"  >>> MISMATCH: judge disagreement, check judge.py prompt or mock evidence")

    if verdict_result["verdict"] != "SUPPORTS":
        blocks = build_intervention_card(
            classification["claim_text"], verdict_result, external_events, []
        )
        print(f"  Card would be posted with {len(blocks)} blocks.")
    else:
        print("  No card posted (claim supported, staying silent).")


if __name__ == "__main__":
    print("Running offline pipeline tests (no Slack connection needed)...")
    print(f"(Pacing calls ~{SECONDS_BETWEEN_CALLS}s apart to respect free tier rate limits -- this will take a few minutes.)")
    for i, (message, expected_is_claim, expected_verdict) in enumerate(TEST_CASES):
        if i > 0:
            time.sleep(SECONDS_BETWEEN_CALLS)
        run_case(message, expected_is_claim, expected_verdict)

    print(f"\n{'='*70}")
    print("Done. Review any '>>> MISMATCH' lines above before connecting to live Slack.")
    print(f"{'='*70}")
