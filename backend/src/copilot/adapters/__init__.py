"""Concrete I/O adapters implementing the port Protocols.

Every cloud/vendor SDK is imported *lazily* inside the method that needs it, so
importing this package (e.g. in tests or the domain) never drags in boto3 or the
Google client. The domain and services depend only on ``ports``; these classes
are wired in at the edges (handlers) or replaced by fakes in tests.
"""

from copilot.adapters.dynamodb_store import DynamoDbStore
from copilot.adapters.gmail_mailbox import GmailMailbox
from copilot.adapters.ja_jobsource import JaJobSource
from copilot.adapters.llm_reply import LlmReplyDrafter

__all__ = ["DynamoDbStore", "GmailMailbox", "JaJobSource", "LlmReplyDrafter"]
