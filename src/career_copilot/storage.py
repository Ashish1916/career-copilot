"""DynamoDB persistence for the hosted agent.

Single table (PK/SK):
  PK="BRIEFING"      SK=<iso-date>   -> the day's rendered briefing + summary
  PK="JOB"           SK=<job_id>     -> a scraped job (for dedup + shortlist)
  PK="PIPELINE"      SK=<app_key>    -> an application's tracked state

Local dev falls back to a JSON file so you can run without AWS.
"""
from __future__ import annotations

import json
import os

TABLE_NAME = os.environ.get("TABLE_NAME", "career-copilot")
_LOCAL_DB = os.environ.get("LOCAL_DB", "")  # set to a path to use file storage


def _table():
    import boto3
    return boto3.resource("dynamodb").Table(TABLE_NAME)


# ---- briefing ---------------------------------------------------------------
def save_briefing(date: str, markdown: str, summary: dict) -> None:
    item = {"PK": "BRIEFING", "SK": date, "markdown": markdown, "summary": summary}
    if _LOCAL_DB:
        _local_put(item)
    else:
        _table().put_item(Item=item)


def latest_briefing() -> dict | None:
    if _LOCAL_DB:
        rows = [r for r in _local_all() if r.get("PK") == "BRIEFING"]
        return max(rows, key=lambda r: r["SK"], default=None)
    from boto3.dynamodb.conditions import Key
    resp = _table().query(
        KeyConditionExpression=Key("PK").eq("BRIEFING"),
        ScanIndexForward=False, Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


# ---- jobs (dedup) -----------------------------------------------------------
def seen_job_ids() -> set[str]:
    if _LOCAL_DB:
        return {r["SK"] for r in _local_all() if r.get("PK") == "JOB"}
    from boto3.dynamodb.conditions import Key
    ids, key = set(), None
    while True:
        kw = {"KeyConditionExpression": Key("PK").eq("JOB"),
              "ProjectionExpression": "SK"}
        if key:
            kw["ExclusiveStartKey"] = key
        page = _table().query(**kw)
        ids.update(i["SK"] for i in page.get("Items", []))
        key = page.get("LastEvaluatedKey")
        if not key:
            return ids


def save_jobs(jobs: list[dict]) -> None:
    for j in jobs:
        item = {"PK": "JOB", "SK": str(j["id"]), **j}
        if _LOCAL_DB:
            _local_put(item)
        else:
            _table().put_item(Item=item)


# ---- tiny local JSON fallback ----------------------------------------------
def _local_all() -> list[dict]:
    if not os.path.exists(_LOCAL_DB):
        return []
    with open(_LOCAL_DB) as f:
        return json.load(f)


def _local_put(item: dict) -> None:
    rows = [r for r in _local_all()
            if not (r.get("PK") == item["PK"] and r.get("SK") == item["SK"])]
    rows.append(item)
    with open(_LOCAL_DB, "w") as f:
        json.dump(rows, f, indent=2)
