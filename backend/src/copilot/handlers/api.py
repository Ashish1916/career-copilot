"""Read API handler: return the caller's latest briefing as JSON.

The user id is the JWT ``sub`` from the API Gateway authorizer (Cognito), so a
caller can only ever read their own briefing. Business logic stays in the
store; this handler only maps request -> user id -> response and adds CORS.
:func:`read_latest` is driven in tests with a fake store.
"""
from __future__ import annotations

import json
from typing import Any

from copilot.adapters.dynamodb_store import DynamoDbStore
from copilot.config import Settings, load_settings
from copilot.domain.briefing import render_markdown
from copilot.ports import StorePort

CORS_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}


def user_id_from_event(event: dict[str, Any]) -> str | None:
    """Extract the JWT ``sub`` from an API Gateway event (pure).

    Supports both HTTP API (``authorizer.jwt.claims``) and REST API
    (``authorizer.claims``) authorizer shapes.
    """
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    claims = authorizer.get("jwt", {}).get("claims") or authorizer.get("claims") or {}
    sub = claims.get("sub")
    return str(sub) if sub else None


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": dict(CORS_HEADERS), "body": json.dumps(body)}


def read_latest(store: StorePort, event: dict[str, Any]) -> dict[str, Any]:
    """Return the latest briefing for the JWT subject as an API response."""
    user_id = user_id_from_event(event)
    if user_id is None:
        return _response(401, {"error": "unauthorized"})

    briefing = store.latest_briefing(user_id)
    if briefing is None:
        return _response(404, {"error": "no_briefing_yet"})

    return _response(
        200,
        {
            "briefing": briefing.model_dump(mode="json"),
            "markdown": render_markdown(briefing),
        },
    )


def build_store(settings: Settings) -> StorePort:
    return DynamoDbStore(settings.table_name, region=settings.aws_region)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for GET /briefing/latest."""
    settings = load_settings()
    return read_latest(build_store(settings), event)
