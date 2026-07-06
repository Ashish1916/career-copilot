from __future__ import annotations

from typing import Protocol

from copilot.domain.models import Email


class LLMPort(Protocol):
    """Draft a reply body for an email. Output is a DRAFT — never auto-sent."""

    def draft_reply(self, email: Email) -> str: ...
