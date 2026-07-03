"""HTTP response helpers — mirrors Crewtron's shared/response.py."""
from __future__ import annotations

import json

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def success(data: dict, status_code: int = 200) -> dict:
    return {"statusCode": status_code, "headers": CORS_HEADERS,
            "body": json.dumps(data, default=str)}


def error(message: str, status_code: int = 400) -> dict:
    return {"statusCode": status_code, "headers": CORS_HEADERS,
            "body": json.dumps({"error": message})}
