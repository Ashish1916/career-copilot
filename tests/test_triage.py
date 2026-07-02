"""Unit tests for the pure classification logic — no network needed."""
from career_copilot import triage


def test_is_job_mail_by_ats_domain():
    assert triage.is_job_mail({"from": "no-reply@us.greenhouse-mail.io", "subject": "Thanks"})
    assert triage.is_job_mail({"from": "x@ashbyhq.com", "subject": "Update"})


def test_is_job_mail_by_subject():
    assert triage.is_job_mail({"from": "a@b.com", "subject": "Thank you for applying to Acme"})


def test_not_job_mail():
    assert not triage.is_job_mail({"from": "deals@nike.com", "subject": "50% off shoes"})


def test_classify_status():
    assert triage.classify_status({"subject": "We'd like to schedule an interview"}) == "interview"
    assert triage.classify_status({"subject": "Your CodeSignal assessment"}) == "assessment"
    assert triage.classify_status({"subject": "Update", "snippet": "unfortunately we will not be moving forward"}) == "rejected"
    assert triage.classify_status({"subject": "Thank you for applying"}) == "applied"
    assert triage.classify_status({"subject": "random"}) == "other"


def test_needs_action():
    assert triage.needs_action({"subject": "Interview invite"})
    assert not triage.needs_action({"subject": "Thank you for applying"})


def test_summarize_counts():
    msgs = [
        {"from": "x@greenhouse-mail.io", "subject": "Thank you for applying"},
        {"from": "r@company.com", "subject": "Schedule an interview"},
        {"from": "deals@nike.com", "subject": "50% off"},
    ]
    s = triage.summarize(msgs)
    assert s["total_scanned"] == 3
    assert s["job_mail"] == 2
    assert s["noise"] == 1
    assert len(s["needs_action"]) == 1
    assert s["by_status"].get("interview") == 1
