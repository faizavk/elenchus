"""
Block Kit card builder.

Only fires a visible card when verdict is CONTRADICTS or INSUFFICIENT with
low/medium confidence -- a clean SUPPORTS verdict stays silent, since the
agent should only speak up when there's something worth flagging.
"""

CONFIDENCE_EMOJI = {
    "High": "🟢",
    "Medium": "🟡",
    "Low": "🔴",
}

VERDICT_HEADER = {
    "CONTRADICTS": "⚠️ Potential Mismatch Detected",
    "INSUFFICIENT": "❓ Unable to Confirm This Claim",
}


def build_intervention_card(claim_text, verdict_result, external_events, slack_evidence_with_links=None):
    verdict = verdict_result["verdict"]
    confidence = verdict_result["confidence"]
    explanation = verdict_result["explanation"]
    recommendation = verdict_result.get("recommendation", "")

    header_text = VERDICT_HEADER.get(verdict, "Notice")
    emoji = CONFIDENCE_EMOJI.get(confidence, "🟡")

    evidence_lines = []
    for e in external_events[:4]:
        evidence_lines.append(f"• {e['summary']} (<{e['link']}|source>)")

    # Slack-native evidence now links to a real permalink instead of quoted
    # text, so the person can jump straight to the original message.
    if slack_evidence_with_links:
        for item in slack_evidence_with_links[:4]:
            if item.get("permalink"):
                evidence_lines.append(f"• \"{item['text'][:80]}\" (<{item['permalink']}|jump to message>)")

    evidence_text = "\n".join(evidence_lines) if evidence_lines else "_No specific external evidence found._"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Claim stated:*\n> {claim_text}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*What the evidence shows:*\n{evidence_text}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Confidence:* {emoji} {confidence}\n*Reasoning:* {explanation}",
            },
        },
    ]

    if recommendation:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommendation:* {recommendation}"},
            }
        )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🔎 Verified automatically by Elenchus — evidence is model-judged, not guaranteed. Please confirm before acting.",
                }
            ],
        }
    )

    return blocks
