"""Integration test for the daily-briefing orchestration using in-memory fakes.

Proves the ports/DI design end-to-end with zero cloud: the same service that
runs in Lambda runs here against fakes.
"""
from collections.abc import Mapping
from datetime import UTC, datetime

from copilot.domain.models import Briefing, Email, Job
from copilot.services.daily_briefing import DailyBriefingService

FIXED_NOW = datetime(2026, 7, 6, 14, 0, 0, tzinfo=UTC)


class FakeMailbox:
    def __init__(self, emails: list[Email]) -> None:
        self._emails = emails
        self.drafts: list[tuple[str, str, str]] = []
        self.sent: list[tuple[str, str, str]] = []

    def fetch_recent(self, *, query: str, max_results: int) -> list[Email]:
        return self._emails[:max_results]

    def create_draft(self, *, to: str, subject: str, body: str) -> None:
        self.drafts.append((to, subject, body))

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class FakeJobs:
    def __init__(self, postings: list[Mapping[str, str]]) -> None:
        self._postings = postings

    def fetch(self) -> list[Mapping[str, str]]:
        return self._postings


class FakeLLM:
    def draft_reply(self, email: Email) -> str:
        return f"Thanks for reaching out about: {email.subject}"


class FakeStore:
    def __init__(self) -> None:
        self.briefings: dict[str, Briefing] = {}
        self.jobs: dict[str, list[Job]] = {}
        self._seen: set[str] = set()

    def save_briefing(self, user_id: str, briefing: Briefing) -> None:
        self.briefings[user_id] = briefing

    def latest_briefing(self, user_id: str) -> Briefing | None:
        return self.briefings.get(user_id)

    def seen_job_ids(self, user_id: str) -> frozenset[str]:
        return frozenset(self._seen)

    def save_jobs(self, user_id: str, jobs: list[Job]) -> None:
        self.jobs.setdefault(user_id, []).extend(jobs)
        self._seen.update(j.id for j in jobs)


def _service(mailbox: FakeMailbox, jobs: FakeJobs, store: FakeStore) -> DailyBriefingService:
    return DailyBriefingService(
        mailbox=mailbox, jobs=jobs, llm=FakeLLM(), store=store,
        min_score=30, now=lambda: FIXED_NOW,
    )


def test_run_produces_briefing_stores_jobs_and_drafts_only():
    mailbox = FakeMailbox([
        Email(sender="Ashby <no-reply@ashbyhq.com>", subject="Interview invitation from Cribl",
              snippet="can we schedule a call?"),
        Email(sender="x@greenhouse.io", subject="Application received",
              snippet="thanks for applying"),
        Email(sender="deals@shop.com", subject="50% off", snippet="sale"),
    ])
    jobs = FakeJobs([
        {"title": "Full Stack Engineer", "company": "Acme", "url": "https://j/1",
         "description": "Flutter AWS Lambda DynamoDB Python full stack"},
        {"title": "Staff Engineer", "company": "Beta", "url": "https://j/2",
         "description": "flutter"},
    ])
    store = FakeStore()

    briefing = _service(mailbox, jobs, store).run(user_id="u1", my_email="me@example.com")

    # Briefing content
    assert briefing.scanned == 3 and briefing.noise == 1
    assert len(briefing.needs_action) == 1                       # only the interview
    assert [j.company for j in briefing.jobs] == ["Acme"]        # staff role filtered out

    # Persisted under the user
    assert store.latest_briefing("u1") is briefing
    assert store.seen_job_ids("u1") == {briefing.jobs[0].id}

    # DRAFTS created, nothing job-related auto-sent; only the self-briefing email was sent
    assert len(mailbox.drafts) == 1
    assert mailbox.drafts[0][1] == "Re: Interview invitation from Cribl"
    assert len(mailbox.sent) == 1 and mailbox.sent[0][0] == "me@example.com"


def test_dedup_against_seen_jobs():
    jobs = FakeJobs([
        {"title": "Software Engineer", "company": "Acme", "url": "https://j/1",
         "description": "python aws"},
    ])
    store = FakeStore()
    svc = _service(FakeMailbox([]), jobs, store)

    first = svc.run(user_id="u1", draft_replies=False)
    assert len(first.jobs) == 1
    second = svc.run(user_id="u1", draft_replies=False)
    assert second.jobs == []  # already seen → not surfaced again


def test_no_email_when_my_email_absent():
    mailbox = FakeMailbox([])
    _service(mailbox, FakeJobs([]), FakeStore()).run(user_id="u1")
    assert mailbox.sent == []
