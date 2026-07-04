"""Tests for the Crewtron-style auth + response helpers."""
import json

from career_copilot import auth, response


def test_extract_user_id_from_jwt_claims():
    event = {"requestContext": {"authorizer": {"claims": {"sub": "user-123"}}}}
    assert auth.extract_user_id(event) == "user-123"


def test_extract_user_id_missing_returns_none():
    assert auth.extract_user_id({}) is None
    assert auth.extract_user_id({"requestContext": {}}) is None


def test_success_response_shape():
    r = response.success({"ok": True})
    assert r["statusCode"] == 200
    assert json.loads(r["body"]) == {"ok": True}
    assert r["headers"]["Access-Control-Allow-Origin"] == "*"


def test_success_custom_status():
    assert response.success({}, status_code=201)["statusCode"] == 201


def test_error_response_shape():
    r = response.error("Unauthorized", 401)
    assert r["statusCode"] == 401
    assert json.loads(r["body"]) == {"error": "Unauthorized"}
