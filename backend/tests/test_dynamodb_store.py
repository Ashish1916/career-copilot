"""Unit tests for the DynamoDB adapter: pure mapping + method wiring on a fake table."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from conftest import make_briefing

from copilot.adapters.dynamodb_store import (
    DynamoDbStore,
    _from_dynamo,
    _to_dynamo,
    briefing_to_item,
    item_to_briefing,
    item_to_job,
    job_to_item,
)
from copilot.domain.models import Briefing, Job


def test_briefing_item_round_trips() -> None:
    briefing = make_briefing()
    item = briefing_to_item("u1", briefing)

    assert item["pk"] == "USER#u1"
    assert item["sk"].startswith("BRIEFING#")
    assert item["type"] == "briefing"
    assert item_to_briefing(item) == briefing


def test_job_item_round_trips() -> None:
    job = Job(id="j1", title="SWE", company="Acme", url="https://x/1", score=55)
    item = job_to_item("u1", job)

    assert item["sk"] == "JOB#j1"
    assert item["job_id"] == "j1"
    assert item_to_job(item) == job


def test_to_dynamo_converts_floats_and_from_dynamo_inverts() -> None:
    converted = _to_dynamo({"a": 1.5, "b": [2.0, 3], "c": {"d": True}})
    assert converted == {"a": Decimal("1.5"), "b": [Decimal("2.0"), 3], "c": {"d": True}}

    restored = _from_dynamo(converted)
    assert restored == {"a": 1.5, "b": [2, 3], "c": {"d": True}}
    # integral Decimals come back as int, not float
    assert isinstance(restored["b"][0], int)
    assert isinstance(restored["a"], float)


def test_to_dynamo_keeps_bool_as_bool() -> None:
    assert _to_dynamo(True) is True
    assert _to_dynamo(False) is False


class _FakeBatch:
    def __init__(self, table: _FakeTable) -> None:
        self._table = table

    def __enter__(self) -> _FakeBatch:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def put_item(self, *, Item: dict[str, Any]) -> None:
        self._table.put_item(Item=Item)


class _FakeTable:
    """Minimal DynamoDB table double keyed on how the store calls it."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def put_item(self, *, Item: dict[str, Any]) -> None:
        key = (Item["pk"], Item["sk"])
        self.items = [i for i in self.items if (i["pk"], i["sk"]) != key]
        self.items.append(Item)

    def batch_writer(self) -> _FakeBatch:
        return _FakeBatch(self)

    def query(self, **kwargs: Any) -> dict[str, Any]:
        if "ProjectionExpression" in kwargs:  # seen_job_ids
            rows = [i for i in self.items if i["type"] == "job"]
        else:  # latest_briefing
            rows = sorted(
                (i for i in self.items if i["type"] == "briefing"),
                key=lambda i: i["sk"],
                reverse=not kwargs.get("ScanIndexForward", True),
            )
            limit = kwargs.get("Limit")
            if limit is not None:
                rows = rows[:limit]
        return {"Items": rows}


def _store() -> tuple[DynamoDbStore, _FakeTable]:
    table = _FakeTable()
    return DynamoDbStore("career-copilot", table=table), table


def test_store_save_and_read_latest_briefing() -> None:
    store, _ = _store()
    briefing = make_briefing()
    assert store.latest_briefing("u1") is None

    store.save_briefing("u1", briefing)
    read = store.latest_briefing("u1")
    assert isinstance(read, Briefing)
    assert read == briefing


def test_store_latest_returns_newest_of_many() -> None:
    store, _ = _store()
    older = make_briefing()
    newer = make_briefing().model_copy(
        update={"generated_at": make_briefing().generated_at.replace(hour=23)}
    )
    store.save_briefing("u1", older)
    store.save_briefing("u1", newer)

    assert store.latest_briefing("u1") == newer


def test_store_save_jobs_and_seen_ids() -> None:
    store, _ = _store()
    jobs = [
        Job(id="j1", title="SWE", company="A", url="https://x/1", score=50),
        Job(id="j2", title="Dev", company="B", url="https://x/2", score=60),
    ]
    store.save_jobs("u1", jobs)
    assert store.seen_job_ids("u1") == {"j1", "j2"}
