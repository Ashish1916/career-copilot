"""DynamoDB persistence — Crewtron-style single table, userId partition key.

  PK=<userId>  SK="BRIEFING#<iso-date>"  -> the day's rendered briefing
  PK=<userId>  SK="JOB#<job_id>"         -> a surfaced job (for dedup)
  PK=<userId>  SK="PIPELINE#<app_key>"   -> an application's tracked state

Tenant isolation is enforced by always scoping queries to the caller's userId,
exactly like Crewtron. Local dev falls back to a JSON file (set LOCAL_DB).
"""
from __future__ import annotations

import json
import os

TABLE_NAME = os.environ.get("TABLE_NAME", "career-copilot")
_LOCAL_DB = os.environ.get("LOCAL_DB", "")  # path -> use file storage for dev


def _table():
    import boto3
    return boto3.resource("dynamodb").Table(TABLE_NAME)


# ---- briefing ---------------------------------------------------------------
def save_briefing(user_id: str, date: str, markdown: str, summary: dict) -> None:
    _put({"PK": user_id, "SK": f"BRIEFING#{date}", "date": date,
          "markdown": markdown, "summary": summary})


def latest_briefing(user_id: str) -> dict | None:
    if _LOCAL_DB:
        rows = [r for r in _local_all()
                if r.get("PK") == user_id and r.get("SK", "").startswith("BRIEFING#")]
        return max(rows, key=lambda r: r["SK"], default=None)
    from boto3.dynamodb.conditions import Key
    resp = _table().query(
        KeyConditionExpression=Key("PK").eq(user_id)
        & Key("SK").begins_with("BRIEFING#"),
        ScanIndexForward=False, Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


# ---- jobs (dedup) -----------------------------------------------------------
def seen_job_ids(user_id: str) -> set[str]:
    prefix = "JOB#"
    if _LOCAL_DB:
        return {r["SK"][len(prefix):] for r in _local_all()
                if r.get("PK") == user_id and r.get("SK", "").startswith(prefix)}
    from boto3.dynamodb.conditions import Key
    ids, key = set(), None
    while True:
        kw = {"KeyConditionExpression": Key("PK").eq(user_id)
              & Key("SK").begins_with(prefix), "ProjectionExpression": "SK"}
        if key:
            kw["ExclusiveStartKey"] = key
        page = _table().query(**kw)
        ids.update(i["SK"][len(prefix):] for i in page.get("Items", []))
        key = page.get("LastEvaluatedKey")
        if not key:
            return ids


def save_jobs(user_id: str, jobs: list[dict]) -> None:
    for j in jobs:
        _put({"PK": user_id, "SK": f"JOB#{j['id']}", **j})


# ---- put + local JSON fallback ---------------------------------------------
def _put(item: dict) -> None:
    if _LOCAL_DB:
        _local_put(item)
    else:
        _table().put_item(Item=item)


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
