"""Claude-drafted Gmail replies for emails that need a human response.

Safety model: Claude only WRITES DRAFTS — they land in Gmail's Drafts folder
for review; nothing is ever auto-sent. Degrades to no-op when
ANTHROPIC_API_KEY isn't configured, so the briefing still ships without it.
"""
from __future__ import annotations

import os

MODEL = "claude-opus-4-8"

_SYSTEM = """You draft email replies for Ashish Kosana, a software engineer at
Crewtron (full-stack: Flutter mobile + AWS serverless) in Tempe, AZ, who is
job-searching. Write the reply he would send: warm, professional, concise
(under 120 words), no fluff. For interview invitations, accept enthusiastically
and offer availability on weekday mornings Arizona time. For assessments,
confirm he'll complete it promptly. Never invent facts about his experience.
Output ONLY the email body — no subject line, no commentary."""


def _client():
    import anthropic
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


def draft_reply(msg: dict) -> str:
    """Draft a reply body for one needs-action email."""
    response = _client().messages.create(
        model=MODEL,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"From: {msg.get('from', '')}\n"
                f"Subject: {msg.get('subject', '')}\n\n"
                f"{msg.get('snippet', '')}\n\n"
                "Draft Ashish's reply."
            ),
        }],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def draft_replies(needs_action: list[dict], gmail_draft_fn) -> int:
    """Create a Gmail draft for each needs-action email. Returns count created.

    gmail_draft_fn(to, subject, body) is injected so this module stays
    Gmail-agnostic and testable.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return 0
    created = 0
    for m in needs_action:
        try:
            body = draft_reply(m)
            if body:
                gmail_draft_fn(m.get("from", ""), f"Re: {m.get('subject', '')}", body)
                created += 1
        except Exception:
            continue  # one bad draft shouldn't sink the briefing
    return created
