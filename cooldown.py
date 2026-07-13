"""
Cooldown tracker.

Notification fatigue is the single most-cited Slack complaint by volume
(1,137+ mentions on G2, and cited as a top-10 business pain point across
148,000+ analyzed complaints). A proactive agent that re-fires on the same
topic repeatedly would make that problem worse, not better -- so Elenchus
tracks which topics it has already flagged recently and stays quiet on
repeats within the cooldown window.

This is intentionally simple (in-memory, per-process) since the hackathon
scope is a single monitored channel in a single running process. A
production version would back this with Redis or similar.
"""

import time

COOLDOWN_SECONDS = 30 * 60  # 30 minutes

_last_flagged_at = {}  # keyword -> timestamp

# Generic action/status words the classifier often includes alongside the
# actual topic (e.g. "finished", "deployed", "confirmed"). These shouldn't
# count for cooldown matching, or one topic's generic word can falsely
# suppress a completely unrelated topic that happens to share it.
_GENERIC_STOPWORDS = {
    "deployed", "deploy", "deployment", "finished", "done", "complete",
    "completed", "decided", "decision", "confirmed", "confirm", "fixed",
    "fix", "migrated", "migration", "launched", "launch", "live", "ready",
    "shipped", "released", "release",
}


def _specific_keywords(keywords):
    """Keeps only topic-specific keywords, dropping generic action words."""
    specific = [k for k in keywords if k.lower() not in _GENERIC_STOPWORDS]
    return specific if specific else keywords  # fall back if everything got filtered


def is_on_cooldown(keywords):
    """
    Returns True if ANY of the given keywords was flagged within the
    cooldown window, meaning we should stay silent this time.
    """
    now = time.time()
    for kw in _specific_keywords(keywords):
        last = _last_flagged_at.get(kw.lower())
        if last and (now - last) < COOLDOWN_SECONDS:
            return True
    return False


def mark_flagged(keywords):
    """Record that these keywords were just flagged, starting a fresh cooldown."""
    now = time.time()
    for kw in _specific_keywords(keywords):
        _last_flagged_at[kw.lower()] = now
