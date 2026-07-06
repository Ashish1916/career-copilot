from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class JobSourcePort(Protocol):
    """Return raw job postings as mappings with at least ``title`` and ``url``."""

    def fetch(self) -> list[Mapping[str, str]]: ...
