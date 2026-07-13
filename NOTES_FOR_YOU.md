# Notes for you — NOT for pasting into Devpost

This file is reminders for recording/submitting. The actual submission
text is in SUBMISSION_TEXT.md — only that file's content should go into
the Devpost form.

## For the demo video

Show the terminal running `test_offline.py` at some point, and say
plainly that the GitHub/deployment data source is seeded for this
sandbox demo, while the claim classification, the MCP connection, the
LLM-as-judge verification, and the Block Kit card generation are all
real, working code, tested independently of that mock data. Stating
this upfront removes any doubt before a judge has to ask about it.

## On honesty about the mocked data

Say plainly, in both the text description and the video narration, that
the external evidence connector runs against seeded data for this
sandbox demo rather than a live production GitHub connection. The MCP
integration itself is real and would swap to a live source without
changing the rest of the pipeline. Stating this clearly protects you
against a judge challenging it later and finding out the hard way.

## Before you submit

- Track: New Slack Agent
- Sandbox access shared to slackhack@salesforce.com and
  testing@devpost.com
- Architecture diagram: architecture_diagram.svg, ready to upload as-is
- Video: under 3 minutes, uploaded to YouTube/Vimeo/Facebook
  Video/Youku, publicly visible, link pasted into the submission form
