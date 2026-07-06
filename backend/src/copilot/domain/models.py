"""Core domain models — immutable, typed, no I/O."""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ApplicationStatus(StrEnum):
    """Where a job application stands, inferred from inbound mail."""

    OFFER = "offer"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    APPLIED = "applied"
    VIEWED = "viewed"
    REJECTED = "rejected"
    OTHER = "other"


# Statuses that genuinely require the candidate to act today.
ACTION_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {ApplicationStatus.OFFER, ApplicationStatus.INTERVIEW, ApplicationStatus.ASSESSMENT}
)


class Email(BaseModel):
    """A fetched inbox message, reduced to what triage needs."""

    model_config = {"frozen": True}

    sender: str
    subject: str
    snippet: str = ""


class TriagedEmail(BaseModel):
    model_config = {"frozen": True}

    email: Email
    is_job_related: bool
    status: ApplicationStatus

    @property
    def needs_action(self) -> bool:
        return self.is_job_related and self.status in ACTION_STATUSES


class Job(BaseModel):
    model_config = {"frozen": True}

    id: str
    title: str
    company: str
    url: str
    location: str = ""
    score: int = Field(default=0, ge=0, le=100)


class Briefing(BaseModel):
    generated_at: datetime
    day: date
    scanned: int
    noise: int
    pipeline: dict[ApplicationStatus, int]
    needs_action: list[TriagedEmail]
    jobs: list[Job]
