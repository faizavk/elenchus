"""
LLM-as-judge contradiction check.

This is the differentiator module -- adapts the uncertainty-sampling /
LLM-as-judge pattern into a single structured call: given a claim and the
evidence gathered from Slack + the mocked GitHub source (+ real RTS results
when available), decide whether the evidence supports, contradicts, or is
insufficient to evaluate the claim.

Uses Groq instead of Gemini for the same free-tier quota reason as
claim_classifier.py.
"""

import json
from groq import Groq

JUDGE_PROMPT = """You are a careful fact-checking judge for a workplace Slack monitoring agent. You will be given a CLAIM someone made in a Slack channel, along with EVIDENCE gathered from recent Slack conversation and from a connected GitHub/deployment data source.

Your job: decide if the evidence SUPPORTS, CONTRADICTS, or is INSUFFICIENT to evaluate the claim. Be conservative -- only say CONTRADICTS if there is a clear, specific conflict. Do not invent evidence that wasn't given to you.

CLAIM: "{claim}"

SLACK CONTEXT (recent messages in the channel, may or may not be relevant):
{slack_context}

EXTERNAL EVIDENCE (from GitHub/deployment source):
{external_evidence}

Respond with ONLY valid JSON, no other text, in this exact format:
{{
  "verdict": "SUPPORTS" or "CONTRADICTS" or "INSUFFICIENT",
  "confidence": "High" or "Medium" or "Low",
  "explanation": "one or two sentence explanation of your reasoning, referencing specific evidence",
  "recommendation": "one short actionable sentence, only if verdict is CONTRADICTS or INSUFFICIENT, else empty string"
}}
"""


def _format_external_evidence(events):
    if not events:
        return "(no matching external events found)"
    lines = []
    for e in events:
        lines.append(f"- [{e['timestamp']}] {e['summary']} (source: {e['link']})")
    return "\n".join(lines)


def _format_slack_context(messages_with_ts):
    if not messages_with_ts:
        return "(no relevant recent Slack messages found)"
    return "\n".join(f"- {text}" for text, ts in messages_with_ts[:10])


def judge_claim(claim_text, slack_context, external_events, model_name="llama-3.1-8b-instant"):
    """
    Returns a dict: {"verdict": str, "confidence": str, "explanation": str, "recommendation": str}
    On failure, defaults to INSUFFICIENT so the agent doesn't falsely accuse anyone
    of a contradiction based on a parsing error.
    """
    client = Groq()  # reads GROQ_API_KEY from environment
    prompt = JUDGE_PROMPT.format(
        claim=claim_text,
        slack_context=_format_slack_context(slack_context),
        external_evidence=_format_external_evidence(external_events),
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        return {
            "verdict": parsed.get("verdict", "INSUFFICIENT"),
            "confidence": parsed.get("confidence", "Low"),
            "explanation": parsed.get("explanation", ""),
            "recommendation": parsed.get("recommendation", ""),
        }
    except Exception as e:
        print(f"[judge] Failed to get judge verdict, defaulting to INSUFFICIENT. Error: {e}")
        return {
            "verdict": "INSUFFICIENT",
            "confidence": "Low",
            "explanation": "Could not evaluate this claim due to an internal error.",
            "recommendation": "",
        }
