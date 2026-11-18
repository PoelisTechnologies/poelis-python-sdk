from __future__ import annotations

from typing import Optional

"""SDK exception hierarchy for Poelis."""


class PoelisError(Exception):
    """Base SDK exception."""


class HTTPError(PoelisError):
    """HTTP error from API response."""

    def __init__(self, status_code: int, message: str | None = None) -> None:
        super().__init__(message or f"HTTP error: {status_code}")
        self.status_code = status_code
        self.message = message or ""


class UnauthorizedError(HTTPError):
    """Raised on 401 Unauthorized."""


class NotFoundError(HTTPError):
    """Raised on 404 Not Found."""


class RateLimitError(HTTPError):
    """Raised on 429 Too Many Requests with optional retry-after seconds."""

    def __init__(self, status_code: int, message: str | None = None, retry_after_seconds: Optional[float] = None) -> None:
        super().__init__(status_code=status_code, message=message)
        self.retry_after_seconds = retry_after_seconds


class ClientError(HTTPError):
    """Raised on other 4xx errors."""


class ServerError(HTTPError):
    """Raised on 5xx errors."""


class PropertyLookupError(PoelisError, RuntimeError):
    """Raised when reading an item's properties fails during a property lookup.

    Covers errors such as a GraphQL error; HTTP and network errors keep their
    own type. The original error is chained as ``__cause__``. It subclasses
    ``RuntimeError`` because the lookup raised ``RuntimeError`` before, so
    ``except RuntimeError`` keeps working.
    """


class UploadError(PoelisError):
    """Raised when a local file cannot be uploaded."""


