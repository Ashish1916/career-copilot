"""AWS Lambda entrypoints for the hosted agent.

Two handlers, one deployment:
  cron_handler  — EventBridge daily: fetch inbox -> triage -> store briefing -> email
  api_handler   — API Gateway GET /briefing: return the latest stored briefing

The Gmail OAuth secret (credentials.json + token.json contents) lives in
Secrets Manager and is materialised to /tmp so the existing gmail_client
functions work unchanged.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import briefing, gmail_client, jobs as jobs_mod, storage
from .triage import summarize

_SECRET_ID = os.environ.get("GMAIL_SECRET_ID", "career-copilot/gmail")
_MY_EMAIL = os.environ.get("MY_EMAIL", "")
_CREDS = "/tmp/credentials.json"
_TOKEN = "/tmp/token.json"


def _materialise_gmail_secret() -> None:
    """Write credentials.json + token.json from Secrets Manager to /tmp."""
    import boto3
    raw = boto3.client("secretsmanager").get_secret_value(SecretId=_SECRET_ID)
    data = json.loads(raw["SecretString"])
    with open(_CREDS, "w") as f:
        json.dump(data["credentials"], f)
    with open(_TOKEN, "w") as f:
        json.dump(data["token"], f)


def cron_handler(event=None, context=None) -> dict:
    _materialise_gmail_secret()
    messages = gmail_client.fetch_recent(
        query="newer_than:2d", max_results=50,
        creds_path=_CREDS, token_path=_TOKEN,
    )
    summary = summarize(messages)

    matches = jobs_mod.top_new_jobs(seen_ids=storage.seen_job_ids())
    if matches:
        storage.save_jobs(matches)
    markdown = briefing.render(summary, jobs=matches)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    storage.save_briefing(date, markdown, summary)

    if _MY_EMAIL:
        gmail_client.send_email(
            _MY_EMAIL, f"☀️ Career Copilot — {date}", markdown,
            creds_path=_CREDS, token_path=_TOKEN,
        )
    return {"date": date, "needs_action": len(summary["needs_action"])}


def api_handler(event=None, context=None) -> dict:
    latest = storage.latest_briefing()
    body = latest or {"markdown": "No briefing yet. Check back after the morning run.",
                      "summary": {}}
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }
