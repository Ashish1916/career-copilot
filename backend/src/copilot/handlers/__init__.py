"""Thin AWS Lambda entrypoints.

Handlers own only wiring + transport concerns: build adapters from ``Settings``,
call a service, and shape the response. All business logic lives in the domain
and services, so handlers stay trivial and are tested with fake adapters.
"""
