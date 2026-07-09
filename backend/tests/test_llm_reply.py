"""Unit tests for the LLM reply drafter: prompt building, degrade, injected client."""
from __future__ import annotations

from typing import Any

from copilot.adapters.llm_reply import LlmReplyDrafter
from copilot.domain.models import Email

_EMAIL = Email(
    sender="recruiter@acme.com",
    subject="Interview invitation",
    snippet="Are you free next week?",
)


def test_build_prompt_includes_email_fields() -> None:
    prompt = LlmReplyDrafter._build_prompt(_EMAIL)
    assert "recruiter@acme.com" in prompt
    assert "Interview invitation" in prompt
    assert "Are you free next week?" in prompt


def test_draft_reply_degrades_to_empty_without_key() -> None:
    assert LlmReplyDrafter(api_key="").draft_reply(_EMAIL) == ""


class _FakeResp:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, *, model: str, contents: str) -> _FakeResp:
        self.calls.append({"model": model, "contents": contents})
        return _FakeResp(self._text)


class _FakeClient:
    def __init__(self, text: str) -> None:
        self.models = _FakeModels(text)


def test_draft_reply_uses_injected_client() -> None:
    client = _FakeClient("  Happy to chat — I'm free Tuesday.  ")
    drafter = LlmReplyDrafter(model="test-model", client=client)

    body = drafter.draft_reply(_EMAIL)

    assert body == "Happy to chat — I'm free Tuesday."
    assert client.models.calls[0]["model"] == "test-model"


def test_draft_reply_empty_text_degrades_to_empty() -> None:
    drafter = LlmReplyDrafter(client=_FakeClient("   "))
    assert drafter.draft_reply(_EMAIL) == ""
