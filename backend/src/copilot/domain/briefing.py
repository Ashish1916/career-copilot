"""Assemble and render the daily briefing from triaged mail + ranked jobs."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from copilot.domain.models import ApplicationStatus, Briefing, Job, TriagedEmail
from copilot.domain.triage import pipeline_counts

_STATUS_ORDER = (
    ApplicationStatus.OFFER,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.ASSESSMENT,
    ApplicationStatus.VIEWED,
    ApplicationStatus.APPLIED,
    ApplicationStatus.REJECTED,
)


def build_briefing(
    triaged: Sequence[TriagedEmail], jobs: Sequence[Job], *, now: datetime
) -> Briefing:
    job_mail = [t for t in triaged if t.is_job_related]
    return Briefing(
        generated_at=now,
        day=now.date(),
        scanned=len(triaged),
        noise=len(triaged) - len(job_mail),
        pipeline=dict(pipeline_counts(triaged)),
        needs_action=[t for t in triaged if t.needs_action],
        jobs=list(jobs),
    )


def render_markdown(b: Briefing) -> str:
    lines: list[str] = ["# ☀️ Career Copilot — Daily Briefing", ""]

    lines.append("## 🔴 Needs you")
    if b.needs_action:
        for t in b.needs_action:
            who = t.email.sender.split("<")[0].strip() or t.email.sender
            lines.append(f"- **{t.status.value.title()}** — {who}: {t.email.subject}")
    else:
        lines.append("- Nothing needs you. ✅")
    lines.append("")

    lines.append("## 🎯 Today's matches")
    if b.jobs:
        for j in b.jobs:
            loc = f" · {j.location}" if j.location else ""
            lines.append(f"- **{j.score}%** — {j.title} @ {j.company}{loc}")
            lines.append(f"  {j.url}")
    else:
        lines.append("- No new roles today.")
    lines.append("")

    lines.append("## 📊 Pipeline")
    parts = [f"{b.pipeline[s]} {s.value}" for s in _STATUS_ORDER if b.pipeline.get(s)]
    lines.append("- " + (" · ".join(parts) if parts else "no application mail yet"))
    lines.append(
        f"- {b.scanned - b.noise} job emails · {b.noise} noise (of {b.scanned} scanned)"
    )
    lines.append("")

    lines.append("## ✅ Today's 15-minute plan")
    lines.append(f"- [ ] Apply to the **{len(b.jobs)}** matches above")
    lines.append("- [ ] Reply to anything under **Needs you**")
    lines.append("- [ ] One outreach message or a LinkedIn comment")
    lines.append("")
    lines.append("_One focused pass, then close the laptop._")
    return "\n".join(lines)
