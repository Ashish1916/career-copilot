from __future__ import annotations

from typing import Protocol

from copilot.domain.models import Briefing, Job


class StorePort(Protocol):
    """Persist briefings + surfaced jobs, scoped per user (tenant isolation)."""

    def save_briefing(self, user_id: str, briefing: Briefing) -> None: ...

    def latest_briefing(self, user_id: str) -> Briefing | None: ...

    def seen_job_ids(self, user_id: str) -> frozenset[str]: ...

    def save_jobs(self, user_id: str, jobs: list[Job]) -> None: ...
