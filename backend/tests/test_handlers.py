"""Handler tests wired with in-memory fakes — no cloud, no network."""
from __future__ import annotations

import json
from typing import Any

from conftest import FakeJobs, FakeLLM, FakeMailbox, FakeStore, make_briefing

from copilot.config import Settings
from copilot.domain.models import Email
from copilot.handlers import api, cron
from copilot.services.daily_briefing import DailyBriefingService


def _service(mailbox: FakeMailbox, jobs: FakeJobs, store: FakeStore) -> DailyBriefingService:
    return DailyBriefingService(
        mailbox=mailbox, jobs=jobs, llm=FakeLLM(), store=store, min_score=30
    )


def test_cron_run_briefing_and_response() -> None:
    mailbox = FakeMailbox(
        [
            Email(
                sender="Ashby <no-reply@ashbyhq.com>",
                subject="Interview invitation",
                snippet="can we schedule a call?",
            ),
            Email(sender="deals@shop.com", subject="50% off", snippet="sale"),
        ]
    )
    jobs = FakeJobs(
        [
            {
                "title": "Full Stack Engineer",
                "company": "Acme",
                "url": "https://j/1",
                "description": "flutter aws python full stack",
            }
        ]
    )
    store = FakeStore()
    settings = Settings(owner_user_id="u1", my_email="me@example.com")

    briefing = cron.run_briefing(_service(mailbox, jobs, store), settings)
    response = cron.briefing_response(briefing)

    assert response == {
        "ok": True,
        "day": briefing.day.isoformat(),
        "scanned": 2,
        "needs_action": 1,
        "jobs": 1,
    }
    # persisted under the owner + self-briefing email sent, replies only drafted
    assert store.latest_briefing("u1") is briefing
    assert len(mailbox.drafts) == 1
    assert mailbox.sent[0][0] == "me@example.com"


def test_cron_build_service_wires_real_adapters() -> None:
    service = cron.build_service(Settings())
    # mypy already proves the port contracts; assert the wiring at runtime too.
    assert isinstance(service, DailyBriefingService)


def _event(sub: str | None, *, rest_shape: bool = False) -> dict[str, Any]:
    if sub is None:
        return {"requestContext": {"authorizer": {}}}
    claims = {"sub": sub}
    authorizer = {"claims": claims} if rest_shape else {"jwt": {"claims": claims}}
    return {"requestContext": {"authorizer": authorizer}}


def test_api_returns_latest_briefing_for_jwt_subject() -> None:
    store = FakeStore()
    briefing = make_briefing()
    store.save_briefing("user-123", briefing)

    resp = api.read_latest(store, _event("user-123"))

    assert resp["statusCode"] == 200
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
    body = json.loads(resp["body"])
    assert body["briefing"]["day"] == briefing.day.isoformat()
    assert body["markdown"].startswith("# ")


def test_api_supports_rest_authorizer_shape() -> None:
    store = FakeStore()
    store.save_briefing("user-123", make_briefing())
    resp = api.read_latest(store, _event("user-123", rest_shape=True))
    assert resp["statusCode"] == 200


def test_api_401_without_subject() -> None:
    resp = api.read_latest(FakeStore(), _event(None))
    assert resp["statusCode"] == 401
    assert json.loads(resp["body"]) == {"error": "unauthorized"}


def test_api_404_when_no_briefing_yet() -> None:
    resp = api.read_latest(FakeStore(), _event("nobody"))
    assert resp["statusCode"] == 404
    assert json.loads(resp["body"]) == {"error": "no_briefing_yet"}


def test_user_id_from_event_none_when_missing() -> None:
    assert api.user_id_from_event({}) is None
