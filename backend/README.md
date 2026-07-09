# career-copilot backend (v2)

A rebuild of the job-search agent to production standards. Runs on **AWS
serverless** with **Google Cloud** for Gmail + Gemini.

## Architecture — ports & adapters (hexagonal)

```
handlers/   thin AWS Lambda entrypoints (cron + read API)
services/   orchestration, wired from injected ports
ports/      Protocol interfaces the services depend on  ← dependency inversion
adapters/   concrete I/O: Gmail API, Gemini, DynamoDB, Secrets Manager, jobs
domain/     pure business logic + typed pydantic models — no I/O, 100% unit-tested
config.py   env-driven settings (pydantic-settings)
logging.py  structured JSON logging
```

The **domain** never imports a cloud SDK; it depends only on `ports`. That keeps
the business rules (triage, scoring, briefing) deterministic and fast to test,
and lets adapters be swapped or faked freely.

## Why this over v1
- Typed pydantic models instead of loose dicts.
- Dependency inversion (ports) → services are testable with fakes; no globals.
- Explicit, tunable SWE scoring profile (v1 surfaced Data-Engineer roles).
- Config, structured logging, strict typing, lint, and CI as first-class.

## Develop
```bash
cd backend
python3.13 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

ruff check src tests     # lint + format checks
mypy src/copilot         # strict type checking
pytest                   # unit tests
```

## Status
- ✅ domain (models, triage, SWE scoring, briefing) + ports + config + logging + tests + CI
- ✅ services (daily-briefing orchestration), wired from ports
- ✅ adapters — DynamoDB store, `ja` job source (SQLite → fixture fallback),
  hosted-LLM reply drafter, Gmail mailbox (SDKs imported lazily)
- ✅ Lambda handlers — daily `cron` + read `api` (JWT `sub` → user id, CORS)
- ⬜ wire OAuth credentials from Secrets Manager (documented TODO in the Gmail adapter)
- ⬜ cut CDK over to this package; deploy (out of scope here)

The adapter SDKs (`boto3`, Google client, LLM SDK) are all imported lazily and
never pulled in by the domain, so the full suite runs with `pip install -e ".[dev]"`
alone — no cloud SDKs, credentials, or network. Install `".[adapters]"` to run
the real cloud path.
