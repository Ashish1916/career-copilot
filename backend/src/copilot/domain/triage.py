"""Pure email triage — classify inbox mail into a pipeline status.

No network: functions take Email values and return classifications, so every
decision is deterministic and unit-testable. The interview rule deliberately
requires *intent* (schedule/invite/…) so marketing like "what's it like to
interview at X?" is not misread as a real interview.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

from copilot.domain.models import ApplicationStatus, Email, TriagedEmail

# Sender fragments that mark ATS / recruiting mail as pipeline-relevant.
ATS_SENDER_FRAGMENTS: tuple[str, ...] = (
    "greenhouse-mail.io", "greenhouse.io", "ashbyhq.com", "lever.co",
    "myworkday.com", "smartrecruiters.com", "jobvite.com", "icims.com",
    "recruiting", "careers", "talent",
)

# Ordered strongest-signal-first; first match wins.
_STATUS_RULES: tuple[tuple[ApplicationStatus, re.Pattern[str]], ...] = (
    (ApplicationStatus.OFFER, re.compile(
        r"pleased to offer|offer of employment|extend(?:ing)? an offer|your offer letter", re.I)),
    (ApplicationStatus.INTERVIEW, re.compile(
        r"(schedule|set ?up|book|invite you)\b.{0,24}(interview|call|screen|chat|conversation|time)"
        r"|phone screen|interview invit(?:e|ation)|interview request"
        r"|would like to (?:interview|speak|chat|meet)|move forward with your"
        r"|next (?:round|steps?)",
        re.I)),
    (ApplicationStatus.ASSESSMENT, re.compile(
        r"assessment|coding challenge|codesignal|hackerrank|online test|take[- ]home"
        r"|complete .{0,20}challenge", re.I)),
    (ApplicationStatus.REJECTED, re.compile(
        r"not moving forward|will not be moving|unfortunately|regret to inform"
        r"|other candidates|position (?:has been )?closed|not (?:be )?selected", re.I)),
    (ApplicationStatus.VIEWED, re.compile(
        r"application was viewed|viewed your application|was sent to the", re.I)),
    (ApplicationStatus.APPLIED, re.compile(
        r"thank you for applying|application received|received your application"
        r"|we(?:'ve| have) received your application|your application (?:for|to|has)", re.I)),
)

_JOB_SUBJECT = re.compile(
    r"applying|your application|application (?:received|viewed)|interview", re.I
)


def is_job_related(email: Email) -> bool:
    sender = email.sender.lower()
    if any(frag in sender for frag in ATS_SENDER_FRAGMENTS):
        return True
    return bool(_JOB_SUBJECT.search(email.subject))


def classify_status(email: Email) -> ApplicationStatus:
    text = f"{email.subject} {email.snippet}"
    for status, pattern in _STATUS_RULES:
        if pattern.search(text):
            return status
    return ApplicationStatus.OTHER


def triage(email: Email) -> TriagedEmail:
    job = is_job_related(email)
    status = classify_status(email) if job else ApplicationStatus.OTHER
    return TriagedEmail(email=email, is_job_related=job, status=status)


def triage_all(emails: Iterable[Email]) -> list[TriagedEmail]:
    return [triage(e) for e in emails]


def pipeline_counts(triaged: Iterable[TriagedEmail]) -> Counter[ApplicationStatus]:
    return Counter(t.status for t in triaged if t.is_job_related)
