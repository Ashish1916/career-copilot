"""Pure job-fit scoring against an explicit keyword profile.

v1 ranked by a résumé-tuned score that surfaced Data-Engineer roles. Here the
profile is explicit and SWE/full-stack, so the ranking reflects the roles
Ashish actually targets. Tune by editing ``SWE_PROFILE`` — no model retraining.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from copilot.domain.models import Job


@dataclass(frozen=True)
class ScoreProfile:
    """Weighted keywords + title gating for scoring a role's fit."""

    keywords: Mapping[str, int]
    title_must_include: tuple[str, ...] = ()
    title_blocklist: tuple[str, ...] = ()

    def matches_title(self, title: str) -> bool:
        t = title.lower()
        if self.title_must_include and not any(k in t for k in self.title_must_include):
            return False
        return not any(b in t for b in self.title_blocklist)


SWE_PROFILE = ScoreProfile(
    keywords={
        "flutter": 15, "dart": 10, "full stack": 12, "full-stack": 12,
        "backend": 10, "software engineer": 10, "python": 10, "typescript": 6,
        "aws": 10, "lambda": 6, "dynamodb": 6, "serverless": 6, "cognito": 4,
        "api gateway": 4, "cdk": 4, "rest": 5, "api": 4, "microservices": 4,
        "docker": 3, "ci/cd": 3, "sql": 3, "mobile": 6, "react": 4, "node": 4,
    },
    title_must_include=("engineer", "developer", "swe", "sde", "full stack", "full-stack"),
    title_blocklist=("senior", "staff", "principal", "lead", "manager", "director", "sr.", "vp"),
)


def score(title: str, description: str, profile: ScoreProfile = SWE_PROFILE) -> int:
    """0-100 keyword-fit score for a role against the profile."""
    text = f"{title} {description}".lower()
    raw = sum(weight for kw, weight in profile.keywords.items() if kw in text)
    return min(100, raw)


def job_id(url: str) -> str:
    """Stable short id keyed on the (unique) posting URL."""
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def rank(
    postings: Sequence[Mapping[str, str]],
    *,
    profile: ScoreProfile = SWE_PROFILE,
    min_score: int = 40,
    limit: int = 8,
    seen: frozenset[str] = frozenset(),
) -> list[Job]:
    """Filter → score → dedup → rank raw postings into Job models, best first.

    Each posting needs at least ``title`` and ``url``; company/location/description
    are optional.
    """
    ranked: list[Job] = []
    for p in postings:
        title, url = p.get("title", ""), p.get("url", "")
        if not title or not url or not profile.matches_title(title):
            continue
        jid = job_id(url)
        if jid in seen:
            continue
        fit = score(title, p.get("description", ""), profile)
        if fit < min_score:
            continue
        ranked.append(
            Job(id=jid, title=title, company=p.get("company", ""),
                url=url, location=p.get("location", ""), score=fit)
        )
    ranked.sort(key=lambda j: j.score, reverse=True)
    return ranked[:limit]
