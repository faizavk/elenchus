"""
Mocked GitHub / deployment state data.

This backs a REAL MCP server (see server.py in this directory) -- the data
itself is seeded/simulated for the hackathon sandbox demo, but it is now
served over the actual Model Context Protocol rather than a same-process
function call. Say this plainly in your submission: the MCP integration
is real, only the underlying repo/deployment data is mocked.

Timestamps are generated relative to "now" each time the server starts,
so a rollback always looks like it happened "a few hours ago" regardless
of when you run the demo.
"""

from datetime import datetime, timedelta

_NOW = datetime.utcnow()


def _hours_ago(h):
    return (_NOW - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M UTC")


# Each entry represents a repo event: commits, PRs, deployments, rollbacks.
# "keywords" are simple terms used to match this event against a claim's topic.
MOCK_EVENTS = [
    {
        "id": "evt-001",
        "type": "deployment_rollback",
        "repo": "payments-service",
        "keywords": ["payments", "payment", "checkout", "billing"],
        "summary": "Deployment of payments-service v2.3.1 was rolled back after checkout failures.",
        "timestamp": _hours_ago(3),
        "link": "https://github.com/example-org/payments-service/actions/runs/9182",
    },
    {
        "id": "evt-002",
        "type": "failing_check",
        "repo": "payments-service",
        "keywords": ["payments", "payment", "checkout", "billing"],
        "summary": "Integration test suite 'checkout_flow' is currently failing on main.",
        "timestamp": _hours_ago(2),
        "link": "https://github.com/example-org/payments-service/pull/441",
    },
    {
        "id": "evt-003",
        "type": "open_pr",
        "repo": "payments-service",
        "keywords": ["payments", "payment", "checkout", "billing"],
        "summary": "PR #441 'Fix checkout race condition' is still open, not yet merged.",
        "timestamp": _hours_ago(5),
        "link": "https://github.com/example-org/payments-service/pull/441",
    },
    {
        "id": "evt-004",
        "type": "merged_pr",
        "repo": "auth-service",
        "keywords": ["oauth", "auth", "login", "authentication"],
        "summary": "PR #218 'Migrate to OAuth2' was merged and deployed successfully to production.",
        "timestamp": _hours_ago(30),
        "link": "https://github.com/example-org/auth-service/pull/218",
    },
    {
        "id": "evt-005",
        "type": "deployment_success",
        "repo": "notifications-service",
        "keywords": ["notifications", "email service", "alerts"],
        "summary": "notifications-service v1.4.0 deployed successfully with no incidents.",
        "timestamp": _hours_ago(20),
        "link": "https://github.com/example-org/notifications-service/actions/runs/771",
    },
]


def query_events(keywords):
    """
    Given keywords extracted from a Slack claim, return matching repo/
    deployment events. Exposed as a real MCP tool by server.py.

    Uses substring matching in both directions (not exact equality) since
    real claim language varies -- "oauth2" should still match an event
    tagged "oauth", "checkout flow" should still match "checkout", etc.
    """
    keywords_lower = [k.lower() for k in keywords]
    matches = []
    for event in MOCK_EVENTS:
        for kw in keywords_lower:
            if any(kw in event_kw or event_kw in kw for event_kw in event["keywords"]):
                matches.append(event)
                break
    return matches
