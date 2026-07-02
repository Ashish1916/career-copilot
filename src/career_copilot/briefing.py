"""Assemble the daily briefing (Markdown) from the triage summary + a plan."""
from __future__ import annotations


def render(summary: dict, plan: dict | None = None) -> str:
    plan = plan or {}
    lines: list[str] = ["# ☀️ Career Copilot — Daily Briefing", ""]

    # 1. Needs action (the only thing that's urgent)
    lines.append("## 🔴 Needs you")
    if summary.get("needs_action"):
        for a in summary["needs_action"]:
            who = a["from"].split("<")[0].strip() or a["from"]
            lines.append(f"- **{a['status'].title()}** — {who}: {a['subject']}")
    else:
        lines.append("- Nothing needs you. ✅")
    lines.append("")

    # 2. Pipeline snapshot
    lines.append("## 📊 Pipeline (last scan)")
    bs = summary.get("by_status", {})
    if bs:
        order = ["offer", "interview", "assessment", "viewed", "applied", "rejected", "other"]
        parts = [f"{bs[s]} {s}" for s in order if bs.get(s)]
        lines.append("- " + " · ".join(parts))
    lines.append(f"- {summary.get('job_mail', 0)} job emails · {summary.get('noise', 0)} noise "
                 f"(of {summary.get('total_scanned', 0)} scanned)")
    lines.append("")

    # 3. Today's plan (the anti-fragmentation checklist)
    lines.append("## ✅ Today's 30-minute plan")
    lines.append(f"- [ ] Apply to **{plan.get('apply', 5)}** curated roles (see job digest)")
    lines.append(f"- [ ] Connect with **{plan.get('connect', 5)}** recruiters/engineers (with a note)")
    lines.append("- [ ] Reply to anything under **Needs you** above")
    lines.append(f"- [ ] {plan.get('linkedin', 'Publish 1 LinkedIn post or comment on 2')}")
    lines.append("")
    lines.append("_One focused pass. Then close the laptop — you did the work._")
    return "\n".join(lines)
