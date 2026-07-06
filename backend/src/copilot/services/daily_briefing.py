"""The daily-briefing orchestration — the product's spine.

Depends only on port Protocols, so it runs identically against real cloud
adapters or in-memory fakes. Safety rule enforced here: replies are created as
DRAFTS, never auto-sent.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from copilot.domain.briefing import build_briefing, render_markdown
from copilot.domain.models import Briefing, TriagedEmail
from copilot.domain.scoring import SWE_PROFILE, ScoreProfile, rank
from copilot.domain.triage import triage_all
from copilot.logging import get_logger
from copilot.ports import JobSourcePort, LLMPort, MailboxPort, StorePort


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class DailyBriefingService:
    mailbox: MailboxPort
    jobs: JobSourcePort
    llm: LLMPort
    store: StorePort
    profile: ScoreProfile = SWE_PROFILE
    min_score: int = 40
    max_jobs: int = 8
    now: Callable[[], datetime] = _utcnow
    log: logging.Logger = field(
        default_factory=lambda: get_logger("copilot.services.daily_briefing")
    )

    def run(
        self,
        *,
        user_id: str,
        my_email: str | None = None,
        query: str = "newer_than:2d",
        max_emails: int = 50,
        draft_replies: bool = True,
    ) -> Briefing:
        """Fetch → triage → rank jobs → store → draft replies → (optional) email."""
        emails = self.mailbox.fetch_recent(query=query, max_results=max_emails)
        triaged = triage_all(emails)

        seen = self.store.seen_job_ids(user_id)
        ranked = rank(
            self.jobs.fetch(),
            profile=self.profile,
            min_score=self.min_score,
            limit=self.max_jobs,
            seen=seen,
        )
        if ranked:
            self.store.save_jobs(user_id, ranked)

        briefing = build_briefing(triaged, ranked, now=self.now())
        self.store.save_briefing(user_id, briefing)

        if draft_replies:
            self._draft_replies(triaged)

        if my_email:
            self.mailbox.send(
                to=my_email,
                subject=f"Career Copilot — {briefing.day.isoformat()}",
                body=render_markdown(briefing),
            )

        self.log.info(
            "daily_briefing_complete",
            extra={"extra_fields": {
                "user_id": user_id,
                "needs_action": len(briefing.needs_action),
                "jobs": len(briefing.jobs),
                "scanned": briefing.scanned,
            }},
        )
        return briefing

    def _draft_replies(self, triaged: list[TriagedEmail]) -> int:
        """Draft a reply per needs-action email (DRAFTS only). One failure never sinks the run."""
        created = 0
        for t in triaged:
            if not t.needs_action:
                continue
            try:
                body = self.llm.draft_reply(t.email)
            except Exception:
                self.log.warning(
                    "draft_reply_failed",
                    extra={"extra_fields": {"subject": t.email.subject}},
                    exc_info=True,
                )
                continue
            if body.strip():
                self.mailbox.create_draft(
                    to=t.email.sender, subject=f"Re: {t.email.subject}", body=body
                )
                created += 1
        return created
