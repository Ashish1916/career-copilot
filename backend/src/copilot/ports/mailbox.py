from __future__ import annotations

from typing import Protocol

from copilot.domain.models import Email


class MailboxPort(Protocol):
    """Read recent mail and create drafts (never auto-send job replies)."""

    def fetch_recent(self, *, query: str, max_results: int) -> list[Email]: ...

    def create_draft(self, *, to: str, subject: str, body: str) -> None: ...

    def send(self, *, to: str, subject: str, body: str) -> None: ...
