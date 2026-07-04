"""Tests for the job engine — reading + de-duping scored roles from ja's DB."""
import sqlite3

import pytest

from career_copilot import jobs


def _make_db(path, rows):
    """Create a minimal ja-shaped jobs table and insert rows."""
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE jobs (title TEXT, company TEXT, location TEXT, url TEXT, "
        "source TEXT, match_score REAL, status TEXT, fetched_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO jobs (title, company, location, url, match_score, status, fetched_at) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()


@pytest.fixture
def ja_db(tmp_path, monkeypatch):
    db = tmp_path / "jobs.db"
    _make_db(str(db), [
        ("Senior SWE", "Acme", "Remote", "https://x.com/1", 95, "new", "2026-07-04"),
        ("Backend Engineer", "Beta", "NYC", "https://x.com/2", 88, "new", "2026-07-03"),
        ("Junior Dev", "Gamma", "SF", "https://x.com/3", 40, "new", "2026-07-02"),   # below min_score
        ("Applied Role", "Delta", "LA", "https://x.com/4", 99, "applied", "2026-07-01"),  # wrong status
    ])
    monkeypatch.setattr(jobs, "JA_DB_PATH", str(db))
    return db


def test_no_db_configured_returns_empty(monkeypatch):
    monkeypatch.setattr(jobs, "JA_DB_PATH", "")
    assert jobs.top_new_jobs(seen_ids=set()) == []


def test_filters_status_and_min_score(ja_db):
    out = jobs.top_new_jobs(seen_ids=set(), min_score=75)
    urls = [j["url"] for j in out]
    assert urls == ["https://x.com/1", "https://x.com/2"]  # junior filtered by score, applied by status


def test_ordered_by_score_desc(ja_db):
    out = jobs.top_new_jobs(seen_ids=set(), min_score=75)
    assert out[0]["score"] >= out[1]["score"]


def test_dedup_against_seen(ja_db):
    first = jobs.top_new_jobs(seen_ids=set(), min_score=75)
    seen = {first[0]["id"]}
    second = jobs.top_new_jobs(seen_ids=seen, min_score=75)
    assert first[0]["id"] not in {j["id"] for j in second}


def test_limit_respected(ja_db):
    assert len(jobs.top_new_jobs(seen_ids=set(), min_score=75, limit=1)) == 1


def test_job_id_stable_and_short():
    a = jobs._job_id("https://x.com/1")
    assert a == jobs._job_id("https://x.com/1")
    assert a != jobs._job_id("https://x.com/2")
    assert len(a) == 16
