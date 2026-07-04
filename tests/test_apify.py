"""Tests for the Apify job engine — scoring, filtering, and safe degradation."""
from career_copilot import apify


def test_no_token_returns_empty(monkeypatch):
    monkeypatch.setattr(apify, "APIFY_TOKEN", "")
    monkeypatch.setattr(apify, "APIFY_ACTOR", "some~actor")
    assert apify.fetch_scored_jobs() == []


def test_no_actor_returns_empty(monkeypatch):
    monkeypatch.setattr(apify, "APIFY_TOKEN", "tok")
    monkeypatch.setattr(apify, "APIFY_ACTOR", "")
    assert apify.fetch_scored_jobs() == []


def test_score_rewards_profile_keywords():
    strong = apify.score("Software Engineer", "Flutter mobile app on AWS Lambda + DynamoDB, Python backend")
    weak = apify.score("Barista", "make coffee, greet customers")
    assert strong > weak
    assert strong <= 100  # capped


def test_score_capped_at_100():
    text = " ".join(apify.PROFILE_KEYWORDS)  # every keyword present
    assert apify.score(text, text) == 100


def test_fetch_filters_and_scores(monkeypatch):
    dataset = [
        {"title": "Software Engineer, Full Stack", "companyName": "Acme",
         "location": "Remote", "url": "https://j/1",
         "description": "Flutter, AWS Lambda, DynamoDB, Python, full stack"},
        {"title": "Staff Engineer", "companyName": "Beta", "url": "https://j/2",
         "description": "Flutter AWS"},                       # senior blocklist
        {"title": "Marketing Manager", "companyName": "Gamma", "url": "https://j/3",
         "description": "brand campaigns"},                   # title must-match fails
        {"title": "Backend Developer", "companyName": "Delta", "url": "https://j/4",
         "description": "make coffee"},                       # score too low
    ]
    monkeypatch.setattr(apify, "APIFY_TOKEN", "tok")
    monkeypatch.setattr(apify, "APIFY_ACTOR", "me~scraper")
    monkeypatch.setattr(apify, "_get", lambda url: dataset)

    out = apify.fetch_scored_jobs(min_score=30)
    urls = [j["url"] for j in out]
    assert urls == ["https://j/1"]
    assert out[0]["company"] == "Acme"
    assert out[0]["score"] >= 30


def test_fetch_skips_items_missing_title_or_url(monkeypatch):
    monkeypatch.setattr(apify, "APIFY_TOKEN", "tok")
    monkeypatch.setattr(apify, "APIFY_ACTOR", "me~scraper")
    monkeypatch.setattr(apify, "_get", lambda url: [
        {"title": "", "url": "https://j/1", "description": "engineer"},
        {"title": "Engineer", "url": "", "description": "engineer"},
    ])
    assert apify.fetch_scored_jobs(min_score=0) == []
