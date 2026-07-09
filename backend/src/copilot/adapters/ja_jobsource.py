"""Job source backed by the local ``ja`` job-application tracker.

``ja`` keeps applications in a small SQLite database. If that DB is present at
``Settings.ja_db_path`` we read postings from it; otherwise we fall back to a
bundled fixture so the pipeline (and the demo) runs with zero setup.

Column names differ between ``ja`` versions, so :func:`_row_to_posting` maps a
raw row onto the ``{title, company, url, location, description}`` shape the
domain scorer expects. Both the fixture path and the row mapping are pure and
unit-tested; only ``_fetch_sqlite`` touches the filesystem.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_FIXTURE = Path(__file__).parent / "fixtures" / "sample_jobs.json"

# Canonical field -> accepted source column aliases (matched case-insensitively).
_FIELD_ALIASES: Mapping[str, tuple[str, ...]] = {
    "title": ("title", "role", "position", "job_title"),
    "company": ("company", "employer", "org", "organization"),
    "url": ("url", "link", "job_url", "href"),
    "location": ("location", "loc", "city", "place"),
    "description": ("description", "desc", "summary", "body", "notes"),
}


def _row_to_posting(row: Mapping[str, Any]) -> dict[str, str]:
    """Map a raw ``ja`` row onto the posting shape the scorer expects (pure)."""
    lower = {str(k).lower(): v for k, v in row.items()}
    posting: dict[str, str] = {}
    for field, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            value = lower.get(alias)
            if value is not None and str(value).strip():
                posting[field] = str(value)
                break
    return posting


class JaJobSource:
    """JobSourcePort reading from the ``ja`` SQLite DB, else a bundled fixture."""

    def __init__(
        self,
        db_path: str = "",
        *,
        table: str = "jobs",
        fixture_path: Path | None = None,
    ) -> None:
        self._db_path = db_path
        self._table = table
        self._fixture_path = fixture_path or _FIXTURE

    def fetch(self) -> list[Mapping[str, str]]:
        if self._db_path and Path(self._db_path).exists():
            return self._fetch_sqlite(self._db_path)
        return self._fetch_fixture()

    def _fetch_sqlite(self, path: str) -> list[Mapping[str, str]]:
        # Read-only connection so we never mutate the user's tracker DB.
        # TODO: the ``ja`` schema/table name is assumed to be ``jobs``; make the
        # table configurable per ``ja`` release if the schema drifts.
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(f"SELECT * FROM {self._table}").fetchall()
        finally:
            con.close()
        postings: list[Mapping[str, str]] = [_row_to_posting(dict(r)) for r in rows]
        return postings

    def _fetch_fixture(self) -> list[Mapping[str, str]]:
        data: Any = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        postings: list[Mapping[str, str]] = [_row_to_posting(row) for row in data]
        return postings
