"""Thin Gmail API wrapper — OAuth + fetch recent messages.

Setup: create an OAuth client (Desktop) in Google Cloud, enable the Gmail API,
download credentials.json into the project root. First run opens a browser to
authorize; the token is cached in token.json.
"""
from __future__ import annotations

import base64
import os

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _service(creds_path: str = "credentials.json", token_path: str = "token.json"):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def fetch_recent(query: str = "newer_than:1d", max_results: int = 40,
                 creds_path: str = "credentials.json", token_path: str = "token.json") -> list[dict]:
    """Return recent messages as [{'from','subject','snippet'}]."""
    svc = _service(creds_path, token_path)
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    out = []
    for ref in resp.get("messages", []):
        m = svc.users().messages().get(
            userId="me", id=ref["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        out.append({
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": m.get("snippet", ""),
        })
    return out


def send_email(to: str, subject: str, body: str,
               creds_path: str = "credentials.json", token_path: str = "token.json") -> None:
    """Send a plain-text email to yourself (the daily briefing)."""
    svc = _service(creds_path, token_path)
    msg = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
    raw = base64.urlsafe_b64encode(msg.encode()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()


def create_draft(to: str, subject: str, body: str,
                 creds_path: str = "credentials.json", token_path: str = "token.json") -> None:
    """Create a draft (never sends) — for Claude-written replies you review."""
    svc = _service(creds_path, token_path)
    msg = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
    raw = base64.urlsafe_b64encode(msg.encode()).decode()
    svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
