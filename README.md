# Career Copilot

A personal job-search agent that ends the fragmentation. Instead of hopping
between LinkedIn, Gmail, job boards, and a tracker in separate sessions, it does
the prep and hands you **one daily briefing** with a 30-minute action plan.

Built to solve my own job search — and built on the stack I work in:
**Python · Gmail API (OAuth) · AWS-ready · Claude API (drafting, planned).**

## What it does (v1)
- **Scans your inbox** (Gmail API) and **triages** it — separates real
  application/recruiter mail from noise.
- **Snapshots your pipeline** — counts by status (applied / interview /
  assessment / offer / rejected) and flags anything that **needs a reply today**.
- **Renders one briefing** (Markdown, optional email) with a focused daily plan.

The classification logic is pure and unit-tested (`career_copilot/triage.py`),
so the "what matters" decisions are verifiable without hitting the network.

## Quickstart
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# Gmail setup: enable the Gmail API in Google Cloud, create an OAuth
# (Desktop) client, download credentials.json into this folder.

copilot briefing              # scan last 24h, print + write briefing.md
copilot briefing --email      # also email the briefing to yourself
copilot briefing --no-gmail   # render without Gmail (offline demo)

pytest                        # run the tests
```

## Roadmap
- **v1** — Gmail triage + pipeline snapshot + daily briefing ✅
- **v2** — job scraping + fit-scoring + tailored-material drafting (Claude API)
- **v3** — LinkedIn post/comment drafts + recruiter shortlist in the briefing
- **v4** — deploy on AWS Lambda (EventBridge daily cron) → briefing lands each morning

## Why it's built this way
The final "apply" / "connect" clicks stay human on purpose — auto-submitting
applications and bulk-connecting violate platform terms and risk account bans.
The copilot removes the 95% that's prep and busywork; you keep the judgment.
