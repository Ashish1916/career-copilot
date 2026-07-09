"""Unit tests for the ja job source: row mapping, fixture fallback, sqlite read."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from copilot.adapters.ja_jobsource import JaJobSource, _row_to_posting


def test_row_to_posting_maps_aliases_case_insensitively() -> None:
    row = {
        "Role": "Backend Engineer",
        "Employer": "Acme",
        "Link": "https://x/1",
        "City": "Remote",
        "Notes": "python aws",
        "ignored": "nope",
    }
    assert _row_to_posting(row) == {
        "title": "Backend Engineer",
        "company": "Acme",
        "url": "https://x/1",
        "location": "Remote",
        "description": "python aws",
    }


def test_row_to_posting_skips_empty_and_none() -> None:
    row = {"title": "SWE", "company": "", "url": None, "location": "   "}
    assert _row_to_posting(row) == {"title": "SWE"}


def test_fetch_uses_bundled_fixture_when_no_db() -> None:
    postings = JaJobSource(db_path="").fetch()
    assert len(postings) >= 3
    assert all("title" in p and "url" in p for p in postings)
    assert any("Flutter" in p.get("description", "") for p in postings)


def test_fetch_reads_from_sqlite_when_present(tmp_path: Path) -> None:
    db = tmp_path / "ja.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE jobs (role TEXT, employer TEXT, link TEXT, notes TEXT)")
    con.execute(
        "INSERT INTO jobs VALUES (?, ?, ?, ?)",
        ("Full Stack Engineer", "Northwind", "https://x/9", "flutter python aws"),
    )
    con.commit()
    con.close()

    postings = JaJobSource(db_path=str(db)).fetch()
    assert postings == [
        {
            "title": "Full Stack Engineer",
            "company": "Northwind",
            "url": "https://x/9",
            "description": "flutter python aws",
        }
    ]


def test_missing_db_path_falls_back_to_fixture(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.db"
    postings = JaJobSource(db_path=str(missing)).fetch()
    assert len(postings) >= 3  # fixture, not an error
