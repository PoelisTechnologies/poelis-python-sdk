from __future__ import annotations

from typing import Any, Optional

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


class UploadError(PoelisError):
    """Raised when a local file cannot be uploaded."""


class GraphQLError(PoelisError, RuntimeError):
    """Raised when the API answers a GraphQL request with errors.

    Subclasses ``RuntimeError``, which these errors used to be, so existing
    ``except RuntimeError`` handlers keep working.

    Attributes:
        errors: The ``errors`` list from the GraphQL response.
        code: ``extensions.code`` of the first error, when the API sets one.
    """

    def __init__(self, errors: Any, message: Optional[str] = None) -> None:
        super().__init__(message if message is not None else str(errors))
        self.errors = errors
        first = errors[0] if isinstance(errors, list) and errors else {}
        self.code: Optional[str] = (first.get("extensions") or {}).get("code") if isinstance(first, dict) else None
