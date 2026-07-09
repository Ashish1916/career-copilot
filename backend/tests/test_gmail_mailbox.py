"""Unit tests for the Gmail adapter: message parsing, encoding, method wiring."""
from __future__ import annotations

import base64
from email import message_from_bytes
from email.policy import default as default_policy
from typing import Any

import pytest

from copilot.adapters.gmail_mailbox import (
    GmailMailbox,
    _encode_message,
    _message_to_email,
)
from copilot.domain.models import Email


def test_message_to_email_parses_headers_and_snippet() -> None:
    message = {
        "snippet": "can we schedule a call?",
        "payload": {
            "headers": [
                {"name": "From", "value": "Ashby <no-reply@ashbyhq.com>"},
                {"name": "Subject", "value": "Interview invitation"},
                {"name": "Delivered-To", "value": "me@example.com"},
            ]
        },
    }
    assert _message_to_email(message) == Email(
        sender="Ashby <no-reply@ashbyhq.com>",
        subject="Interview invitation",
        snippet="can we schedule a call?",
    )


def test_message_to_email_tolerates_missing_fields() -> None:
    assert _message_to_email({}) == Email(sender="", subject="", snippet="")


def test_encode_message_round_trips_via_rfc2822() -> None:
    raw = _encode_message(to="you@x.com", subject="Re: Hi", body="Hello there\n")
    parsed = message_from_bytes(base64.urlsafe_b64decode(raw), policy=default_policy)
    assert parsed["To"] == "you@x.com"
    assert parsed["Subject"] == "Re: Hi"
    assert parsed.get_content().strip() == "Hello there"


class _Executable:
    def __init__(self, result: Any) -> None:
        self._result = result

    def execute(self) -> Any:
        return self._result


class _Messages:
    def __init__(self, service: _FakeService) -> None:
        self._service = service

    def list(self, **kwargs: Any) -> _Executable:
        self._service.list_calls.append(kwargs)
        return _Executable({"messages": [{"id": "m1"}]})

    def get(self, **kwargs: Any) -> _Executable:
        return _Executable(
            {
                "snippet": "hi",
                "payload": {"headers": [{"name": "From", "value": "a@b.com"}]},
            }
        )

    def send(self, **kwargs: Any) -> _Executable:
        self._service.sent.append(kwargs)
        return _Executable({"id": "sent1"})


class _Drafts:
    def __init__(self, service: _FakeService) -> None:
        self._service = service

    def create(self, **kwargs: Any) -> _Executable:
        self._service.drafts.append(kwargs)
        return _Executable({"id": "draft1"})


class _Users:
    def __init__(self, service: _FakeService) -> None:
        self._service = service

    def messages(self) -> _Messages:
        return _Messages(self._service)

    def drafts(self) -> _Drafts:
        return _Drafts(self._service)


class _FakeService:
    def __init__(self) -> None:
        self.list_calls: list[dict[str, Any]] = []
        self.sent: list[dict[str, Any]] = []
        self.drafts: list[dict[str, Any]] = []

    def users(self) -> _Users:
        return _Users(self)


def test_fetch_recent_lists_then_hydrates_each_message() -> None:
    svc = _FakeService()
    mailbox = GmailMailbox(service=svc)

    emails = mailbox.fetch_recent(query="newer_than:2d", max_results=10)

    assert emails == [Email(sender="a@b.com", subject="", snippet="hi")]
    assert svc.list_calls[0]["q"] == "newer_than:2d"


def test_create_draft_and_send_encode_body() -> None:
    svc = _FakeService()
    mailbox = GmailMailbox(service=svc)

    mailbox.create_draft(to="x@y.com", subject="Re: Hi", body="draft body")
    mailbox.send(to="me@x.com", subject="Briefing", body="today")

    assert svc.drafts[0]["body"]["message"]["raw"]
    assert svc.sent[0]["body"]["raw"]


def test_missing_credentials_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="credentials are not configured"):
        GmailMailbox().fetch_recent(query="", max_results=1)
