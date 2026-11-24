from __future__ import annotations

from typing import Optional

"""SDK exception hierarchy for Poelis."""


class PoelisError(Exception):
    """Base SDK exception."""


class HTTPError(PoelisError):
    """Error returned by the Poelis API."""

    def __init__(
        self, status_code: int, message: str | None = None, error_code: str | None = None
    ) -> None:
        super().__init__(message or f"HTTP error: {status_code}")
        self.status_code = status_code
        self.message = message or ""
        # Machine-readable code from the API, for example "not_found" or "no_blob".
        self.error_code = error_code


class UnauthorizedError(HTTPError):
    """Raised on 401 Unauthorized."""


class NotFoundError(HTTPError):
    """Raised on 404 Not Found."""


class RateLimitError(HTTPError):
    """Raised on 429 Too Many Requests with optional retry-after seconds."""

    def __init__(
        self,
        status_code: int,
        message: str | None = None,
        retry_after_seconds: Optional[float] = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(status_code=status_code, message=message, error_code=error_code)
        self.retry_after_seconds = retry_after_seconds


class ClientError(HTTPError):
    """Raised on other 4xx errors."""


class InvalidInputError(ClientError):
    """Raised when the API rejects a value sent by the caller."""


class ServerError(HTTPError):
    """Raised on 5xx errors."""


class NetworkError(PoelisError):
    """Raised when the Poelis API cannot be reached."""


class PropertyLookupError(PoelisError):
    """Raised when reading an item's properties fails during a property lookup.

    API and network errors keep their own type. The original error is chained
    as ``__cause__``.
    """


class AmbiguousKeyError(PoelisError):
    """Raised when a key matches more than one item or property under the same parent.

    A key is unique in the draft, but renaming a key applies to every published
    version, so an older version can hold two rows with the same key.
    """


class UploadError(PoelisError):
    """Raised when a local file cannot be uploaded."""


class FileNotDownloadableError(ClientError):
    """Raised when a file has no stored bytes to download.

    Documents written inside Poelis are stored as editor content, not as a
    file, so they cannot be downloaded through the SDK yet.
    """


