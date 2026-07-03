"""Job engine — surface today's best matches from the `ja` (job-apply) store.

`ja` already fetches from many ATS sources and scores each role against the
résumé, writing them to a local SQLite DB. We read the top *new* matches from
there and de-dup against jobs we've already surfaced.

In the cloud (Lambda) that SQLite file isn't present, so this degrades
gracefully to [] — the briefing still ships with the inbox section. Porting
the fetchers so the cron can refresh jobs server-side is the v2 step.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3

# Path to job-apply's SQLite DB. Set locally; absent in Lambda -> no jobs.
JA_DB_PATH = os.environ.get("JA_DB_PATH", "")


def _job_id(url: str) -> str:
    """Stable short id for a role, keyed on its (unique) URL."""
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def top_new_jobs(seen_ids: set[str], limit: int = 8, min_score: int = 75) -> list[dict]:
    """Top-scored `new` roles not yet surfaced, best first."""
    if not JA_DB_PATH or not os.path.exists(JA_DB_PATH):
        return []
    conn = sqlite3.connect(JA_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT title, company, location, url, match_score "
            "FROM jobs WHERE status = 'new' AND match_score >= ? "
            "ORDER BY match_score DESC, fetched_at DESC LIMIT 300",
            (min_score,),
        ).fetchall()
    finally:
        conn.close()

    out: list[dict] = []
    for r in rows:
        jid = _job_id(r["url"])
        if jid in seen_ids:
            continue
        out.append({
            "id": jid,
            "title": r["title"],
            "company": r["company"],
            "location": r["location"] or "",
            "url": r["url"],
            "score": round(r["match_score"] or 0),
        })
        if len(out) >= limit:
            break
    return out
