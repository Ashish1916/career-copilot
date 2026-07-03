"""Apify job-scraping engine — the cloud replacement for local `ja` fetchers.

An Apify actor (e.g. a LinkedIn/Indeed jobs scraper) runs on a schedule in
Apify's cloud; we pull its latest dataset here, normalise the items, and
keyword-score them against the profile. No browser, no scraping from Lambda —
Apify does the fetching, we do the ranking.

Degrades to [] when APIFY_TOKEN isn't configured, so the briefing still ships.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
# Actor whose last run's dataset we read, e.g. "bebity~linkedin-jobs-scraper".
APIFY_ACTOR = os.environ.get("APIFY_ACTOR", "")

# Keyword profile for fit-scoring (mirrors the résumé's SWE positioning).
PROFILE_KEYWORDS = {
    "flutter": 15, "dart": 10, "aws": 12, "lambda": 8, "dynamodb": 8,
    "serverless": 8, "python": 10, "typescript": 8, "api gateway": 6,
    "cognito": 5, "cdk": 5, "full stack": 10, "full-stack": 10,
    "backend": 8, "mobile": 8, "software engineer": 10, "react": 4,
    "rest": 4, "microservices": 4, "ci/cd": 3, "sql": 3,
}
TITLE_MUST_MATCH = ("engineer", "developer", "swe")
SENIOR_BLOCKLIST = ("staff", "principal", "director", "manager", "lead", "sr.", "senior")


def _get(url: str) -> list | dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def _job_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def score(title: str, description: str) -> int:
    """0-100 keyword fit against the SWE profile."""
    text = f"{title} {description}".lower()
    raw = sum(w for kw, w in PROFILE_KEYWORDS.items() if kw in text)
    return min(100, raw)


def fetch_scored_jobs(limit: int = 25, min_score: int = 30) -> list[dict]:
    """Latest actor-run dataset -> normalised, scored, entry-level-ish jobs."""
    if not APIFY_TOKEN or not APIFY_ACTOR:
        return []
    actor = urllib.parse.quote(APIFY_ACTOR, safe="~")
    items = _get(
        f"https://api.apify.com/v2/acts/{actor}/runs/last/dataset/items"
        f"?token={APIFY_TOKEN}&status=SUCCEEDED"
    )

    out: list[dict] = []
    for it in items:
        title = it.get("title") or it.get("positionName") or ""
        url = it.get("url") or it.get("link") or it.get("jobUrl") or ""
        if not title or not url:
            continue
        tl = title.lower()
        if not any(k in tl for k in TITLE_MUST_MATCH):
            continue
        if any(k in tl for k in SENIOR_BLOCKLIST):
            continue
        s = score(title, it.get("description") or it.get("descriptionText") or "")
        if s < min_score:
            continue
        out.append({
            "id": _job_id(url),
            "title": title,
            "company": it.get("companyName") or it.get("company") or "",
            "location": it.get("location") or "",
            "url": url,
            "score": s,
        })
    out.sort(key=lambda j: j["score"], reverse=True)
    return out[:limit]
