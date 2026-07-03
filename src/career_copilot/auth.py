"""Auth helper — mirrors Crewtron's shared/auth_utils.py.

The API Gateway Cognito authorizer injects the verified JWT claims into the
event; the user's identity is the Cognito `sub`. We never trust the body.
"""
from __future__ import annotations


def extract_user_id(event: dict) -> str | None:
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
        .get("sub")
    )
