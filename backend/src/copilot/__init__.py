"""career-copilot — a personal job-search agent.

Architecture (ports & adapters / hexagonal):
    domain/   pure business logic + typed models — no I/O, fully unit-tested
    ports/    Protocol interfaces the domain depends on (dependency inversion)
    adapters/ concrete I/O implementations (Gmail, Gemini, DynamoDB, ...)
    services/ orchestration wired from injected ports
    handlers/ thin AWS Lambda entrypoints
"""

__version__ = "2.0.0"
