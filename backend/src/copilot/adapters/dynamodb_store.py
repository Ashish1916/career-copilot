"""DynamoDB-backed :class:`~copilot.ports.store.StorePort`.

Single-table design, one partition per user (tenant isolation)::

    pk                sk                              type
    USER#<user_id>    BRIEFING#<generated_at_iso>     briefing
    USER#<user_id>    JOB#<job_id>                    job

Briefings and jobs are stored as their pydantic ``model_dump(mode="json")``
payloads, so the mapping stays schema-driven and round-trips exactly. DynamoDB
represents every number as :class:`decimal.Decimal`; the ``_to_dynamo`` /
``_from_dynamo`` helpers make writes and reads Decimal-safe and are pure, so
the mapping is unit-tested without any AWS calls.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from copilot.domain.models import Briefing, Job


def _pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _to_dynamo(value: Any) -> Any:
    """Recursively convert a JSON-safe value into a DynamoDB-safe one.

    ``float`` is unsupported by DynamoDB and must be ``Decimal``; everything
    else (str/int/bool/None/list/dict) passes through unchanged.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_to_dynamo(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_dynamo(v) for k, v in value.items()}
    return value


def _from_dynamo(value: Any) -> Any:
    """Inverse of :func:`_to_dynamo`: turn ``Decimal`` back into int/float."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [_from_dynamo(v) for v in value]
    if isinstance(value, dict):
        return {k: _from_dynamo(v) for k, v in value.items()}
    return value


def briefing_to_item(user_id: str, briefing: Briefing) -> dict[str, Any]:
    """Map a :class:`Briefing` to a DynamoDB item (pure)."""
    return {
        "pk": _pk(user_id),
        "sk": f"BRIEFING#{briefing.generated_at.isoformat()}",
        "type": "briefing",
        "user_id": user_id,
        "day": briefing.day.isoformat(),
        "payload": _to_dynamo(briefing.model_dump(mode="json")),
    }


def item_to_briefing(item: dict[str, Any]) -> Briefing:
    """Rebuild a :class:`Briefing` from a stored item (pure)."""
    return Briefing.model_validate(_from_dynamo(item["payload"]))


def job_to_item(user_id: str, job: Job) -> dict[str, Any]:
    """Map a :class:`Job` to a DynamoDB item (pure)."""
    return {
        "pk": _pk(user_id),
        "sk": f"JOB#{job.id}",
        "type": "job",
        "user_id": user_id,
        "job_id": job.id,
        "payload": _to_dynamo(job.model_dump(mode="json")),
    }


def item_to_job(item: dict[str, Any]) -> Job:
    """Rebuild a :class:`Job` from a stored item (pure)."""
    return Job.model_validate(_from_dynamo(item["payload"]))


class DynamoDbStore:
    """StorePort backed by a DynamoDB table (boto3 imported lazily).

    A ``table`` resource may be injected (tests / reuse); otherwise it is
    created on first use so importing this module needs no AWS credentials.
    """

    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        table: Any | None = None,
    ) -> None:
        self._table_name = table_name
        self._region = region
        self._table: Any | None = table

    @property
    def table(self) -> Any:
        if self._table is None:
            import boto3

            self._table = boto3.resource("dynamodb", region_name=self._region).Table(
                self._table_name
            )
        return self._table

    def save_briefing(self, user_id: str, briefing: Briefing) -> None:
        self.table.put_item(Item=briefing_to_item(user_id, briefing))

    def latest_briefing(self, user_id: str) -> Briefing | None:
        from boto3.dynamodb.conditions import Key

        resp = self.table.query(
            KeyConditionExpression=Key("pk").eq(_pk(user_id))
            & Key("sk").begins_with("BRIEFING#"),
            ScanIndexForward=False,  # newest sk first
            Limit=1,
        )
        items = resp.get("Items", [])
        if not items:
            return None
        return item_to_briefing(items[0])

    def seen_job_ids(self, user_id: str) -> frozenset[str]:
        from boto3.dynamodb.conditions import Key

        condition = Key("pk").eq(_pk(user_id)) & Key("sk").begins_with("JOB#")
        ids: set[str] = set()
        start_key: dict[str, Any] | None = None
        while True:
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": condition,
                "ProjectionExpression": "job_id",
            }
            if start_key is not None:
                kwargs["ExclusiveStartKey"] = start_key
            resp = self.table.query(**kwargs)
            ids.update(str(i["job_id"]) for i in resp.get("Items", []))
            start_key = resp.get("LastEvaluatedKey")
            if not start_key:
                break
        return frozenset(ids)

    def save_jobs(self, user_id: str, jobs: list[Job]) -> None:
        with self.table.batch_writer() as batch:
            for job in jobs:
                batch.put_item(Item=job_to_item(user_id, job))
