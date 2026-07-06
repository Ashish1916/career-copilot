"""Port interfaces (Protocols) the services depend on.

The domain and services import only these; concrete I/O lives in ``adapters`` and
is injected at the edges. This keeps business logic testable with fakes.
"""

from copilot.ports.jobsource import JobSourcePort
from copilot.ports.llm import LLMPort
from copilot.ports.mailbox import MailboxPort
from copilot.ports.store import StorePort

__all__ = ["JobSourcePort", "LLMPort", "MailboxPort", "StorePort"]
