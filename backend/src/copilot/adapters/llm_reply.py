"""LLM-backed reply drafter implementing :class:`~copilot.ports.llm.LLMPort`.

Provider-agnostic by design: the hosted-LLM SDK is imported lazily and hidden
behind a small ``client`` seam, so the class name and public contract carry no
vendor. Output is always a *draft* — the service never auto-sends it.

Graceful degradation: with no API key (local dev, missing secret) the internal
generator returns ``None`` and :meth:`draft_reply` yields ``""``, which the
service reads as "no draft" — the daily run still completes.
"""
from __future__ import annotations

from typing import Any

from copilot.domain.models import Email

_SYSTEM = (
    "You are helping a software engineer reply to a recruiting email. "
    "Write a short, warm, professional reply in first person. "
    "Confirm interest, offer availability, and keep it under 120 words. "
    "Do not invent specific dates, salary numbers, or commitments."
)


class LlmReplyDrafter:
    """LLMPort that drafts a reply via a hosted LLM (SDK imported lazily)."""

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "gemini-2.0-flash",
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    def draft_reply(self, email: Email) -> str:
        """Return a draft body, or ``""`` when the LLM is unavailable."""
        return self._generate(email) or ""

    def _generate(self, email: Email) -> str | None:
        client = self._get_client()
        if client is None:
            return None
        resp = client.models.generate_content(
            model=self._model, contents=self._build_prompt(email)
        )
        text = getattr(resp, "text", None)
        if not text:
            return None
        drafted = str(text).strip()
        return drafted or None

    def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        if not self._api_key:
            return None
        from google import genai

        self._client = genai.Client(api_key=self._api_key)
        return self._client

    @staticmethod
    def _build_prompt(email: Email) -> str:
        """Assemble the prompt from an email (pure, unit-tested)."""
        return (
            f"{_SYSTEM}\n\n"
            f"From: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Preview: {email.snippet}\n\n"
            "Draft the reply body only (no subject line):"
        )
