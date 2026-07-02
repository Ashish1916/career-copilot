"""Pure, testable classification of job-search emails.

No network here — these functions take already-fetched message dicts
({"from","subject","snippet"}) and classify them, so they're unit-testable.
"""
from __future__ import annotations

import re

# ATS / recruiting sender domains → a message from one of these is pipeline mail.
ATS_DOMAINS = (
    "greenhouse-mail.io", "greenhouse.io", "ashbyhq.com", "myworkday.com",
    "smartrecruiters.com", "jobvite.com", "talent.icims.com", "lever.co",
    "recruiting", "careers", "no-reply@openai.com", "makenotion.com",
)

# Status detection — order matters (strongest signal first).
_STATUS_RULES = (
    ("offer", r"\boffer\b|pleased to offer|extend an offer"),
    ("interview", r"interview|phone screen|schedule (a|your)|availability|move forward|next step|meet with"),
    ("assessment", r"assessment|coding challenge|codesignal|hackerrank|online test|take[- ]home"),
    ("rejected", r"not moving forward|unfortunately|regret to|other candidates|will not be|not be moving"),
    ("viewed", r"application was viewed|viewed your application"),
    ("applied", r"thank you for applying|application received|we(?:'ve| have) received your application|your application"),
)

NEEDS_ME = ("offer", "interview", "assessment")


def is_job_mail(msg: dict) -> bool:
    """True if the email looks like a real job-application/recruiter message."""
    sender = (msg.get("from") or "").lower()
    subject = (msg.get("subject") or "").lower()
    if any(d in sender for d in ATS_DOMAINS):
        return True
    return bool(re.search(r"applying|your application|application (received|viewed)|interview", subject))


def classify_status(msg: dict) -> str:
    """Return one of: offer|interview|assessment|rejected|viewed|applied|other."""
    text = f"{msg.get('subject','')} {msg.get('snippet','')}".lower()
    for status, pattern in _STATUS_RULES:
        if re.search(pattern, text):
            return status
    return "other"


def needs_action(msg: dict) -> bool:
    """Does this genuinely need a human reply today?"""
    return classify_status(msg) in NEEDS_ME


def summarize(messages: list[dict]) -> dict:
    """Roll a list of fetched messages into a briefing-ready summary."""
    job = [m for m in messages if is_job_mail(m)]
    by_status: dict[str, int] = {}
    action_items: list[dict] = []
    for m in job:
        s = classify_status(m)
        by_status[s] = by_status.get(s, 0) + 1
        if s in NEEDS_ME:
            action_items.append({"from": m.get("from", ""), "subject": m.get("subject", ""), "status": s})
    return {
        "total_scanned": len(messages),
        "job_mail": len(job),
        "by_status": by_status,
        "needs_action": action_items,
        "noise": len(messages) - len(job),
    }
