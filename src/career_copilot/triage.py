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
    ("offer", r"pleased to offer|extend(?:ing)? an offer|offer of employment|your offer|job offer"),
    # Require real intent — not just the word "interview" (kills marketing like
    # "What's it like to interview at X?" / "interview tips").
    ("interview", r"(schedule|set ?up|book|invite you)\b.{0,24}(interview|call|screen|chat|conversation|time)"
                  r"|phone screen|interview invit(e|ation)|interview request|would like to (interview|speak|chat|meet)"
                  r"|move forward with your|next (round|step|steps) in"),
    ("assessment", r"assessment|coding challenge|codesignal|hackerrank|online test|take[- ]home|complete .{0,20}challenge"),
    ("rejected", r"not moving forward|will not be moving|unfortunately|regret to inform|other candidates|position (has been )?closed|not (be )?selected"),
    ("viewed", r"application was viewed|viewed your application|was sent to"),
    ("applied", r"thank you for applying|application received|received your application|we(?:'ve| have) received your application|your application (for|to|is)"),
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
