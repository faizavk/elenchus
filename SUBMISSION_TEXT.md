Short description (for the summary field):

Signal watches a Slack channel for status and decision claims like "we
deployed X" or "we finished Y," checks them against recent Slack context
and connected system data, and speaks up only when something doesn't add
up. If the claim checks out, it stays silent.

---

Full text description:

Most workplace AI in Slack today is reactive. Someone asks a question,
the bot searches for an answer, and hopes it found the right thing. That
model has a real weakness: it can only correct a wrong belief if someone
thinks to ask.

Signal works differently. It monitors a channel in the background and
watches for claims people make in passing, statements like "we deployed
payments yesterday" or "the migration is done." Instead of waiting to be
asked, it checks the claim itself.

When a claim comes in, Signal:

1. Classifies whether it's actually a status or decision claim worth
checking, so it stays quiet on small talk and general chat.
2. Gathers evidence from two places: recent conversation in the same
Slack channel, and a connected system that tracks deployment and commit
activity, retrieved over a real MCP (Model Context Protocol) connection.
The repo/deployment data behind that connector is seeded for this
hackathon sandbox, standing in for a live GitHub feed, but the MCP
server and client are genuine and protocol-compliant.
3. Runs an LLM-as-judge check to decide if the evidence supports,
contradicts, or can't confirm the claim, and estimates a confidence
level for that verdict.
4. If the claim holds up, Signal says nothing. If it doesn't, or if
there isn't enough evidence to be sure, Signal posts a card directly in
the thread showing what was claimed, what the evidence actually shows,
and a confidence level, so the correction shows up exactly where the
wrong claim was made.

This came out of earlier work I did on hallucination detection in LLMs,
specifically LLM-as-judge verification and uncertainty estimation. That
research became the core mechanism here instead of a side feature.

The goal isn't to build another Q&A bot. It's to catch the moment a team
is about to act on something that's already out of date, before that
turns into a wrong deployment, a duplicated fix, or a decision made on
stale information.

Slack's own help documentation acknowledges that Slackbot and Slack AI
can hallucinate, meaning generate answers that sound confident and
plausible but are factually wrong. Their current guidance for catching
this is manual: ask the same question again, keep conversations short,
or provide more specific sources yourself. There is no automated check.
Signal adds that missing layer. Alongside the automatic monitoring, a
"Verify with Signal" message shortcut lets anyone right-click any
message, including a Slack AI answer, and get an evidence-based check
on demand. It is the automated version of the manual workaround Slack
currently asks users to do by hand.

Two design choices came directly from looking at what people actually
complain about with Slack rather than assuming. Evidence citations link
to real permalinks instead of quoted text, because a heavily-repeated
complaint is that finding an old message again requires already knowing
what to search for, which defeats the purpose. And Signal will not
re-flag the same topic within a 30 minute window, because notification
fatigue is the single most cited Slack complaint by volume. A proactive
agent that fires repeatedly on one topic would make that problem worse
instead of solving anything.

Silence is the core feature here, not a side effect. In testing, Signal
stays quiet on the large majority of messages in a channel, because most
claims people make are simply true. It only speaks when the evidence
disagrees with what was said. A monitoring agent that comments on every
claim, even to confirm it, becomes noise. One that speaks up only when
something is actually wrong is the difference between a useful teammate
and an annoying bot.

---

Track: New Slack Agent

---

Technologies used:

- Slack Bolt + Socket Mode (Slack Agent)
- A real MCP server and client for the evidence connector
- Real-Time Search API (assistant.search.context), activated when the
bot is @-mentioned directly in a claim
- Slack conversation history for in-channel context on passive
monitoring
- Groq (Llama 3.1) for claim classification and LLM-as-judge
verification
