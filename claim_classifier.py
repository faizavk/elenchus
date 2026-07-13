"""
Claim classifier.

Cheap, fast Groq call whose only job is to decide:
  1. Is this message an important status/decision claim? (vs small talk, questions, jokes)
  2. If yes, what's the short factual claim, and what topic keywords describe it?

This runs on every message in the monitored channel, so it needs to be fast
and needs to correctly stay silent on most messages. If this fires on every
message, the demo will look spammy and fake.

Uses Groq instead of Gemini: Groq's free tier gives a much higher daily
request quota (reported ~1,000-14,400/day depending on model), which matters
since this classifier runs on every single message in the channel.
"""

import json
from groq import Groq

CLASSIFIER_PROMPT = """You are a filter for a Slack monitoring agent. Your only job is to decide whether a message contains an important STATUS or DECISION claim that a team might act on -- for example, claims about something being deployed, finished, fixed, migrated, decided, or confirmed.

Do NOT flag: questions, greetings, jokes, opinions, vague chat, or claims with no concrete verifiable status.

DO flag: statements like "we deployed X", "we finished Y", "we decided to use Z", "the migration is done", "this is fixed now".

Message: "{message}"

Respond with ONLY valid JSON, no other text, in this exact format:
{{"is_claim": true or false, "claim_text": "short restatement of the claim if is_claim is true, else empty string", "keywords": ["topic", "keywords", "for", "search"]}}
"""


def classify_message(message_text, model_name="llama-3.1-8b-instant"):
    """
    Returns a dict: {"is_claim": bool, "claim_text": str, "keywords": [str]}
    Falls back to is_claim=False on any parsing error, since staying silent
    is the safe failure mode here.
    """
    client = Groq()  # reads GROQ_API_KEY from environment
    prompt = CLASSIFIER_PROMPT.format(message=message_text)

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
            "is_claim": bool(parsed.get("is_claim", False)),
            "claim_text": parsed.get("claim_text", ""),
            "keywords": parsed.get("keywords", []),
        }
    except Exception as e:
        print(f"[claim_classifier] Failed to classify message, defaulting to non-claim. Error: {e}")
        return {"is_claim": False, "claim_text": "", "keywords": []}
