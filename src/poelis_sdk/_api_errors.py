"""Turn the errors of an API response into SDK exceptions."""

from __future__ import annotations

import re
from typing import Any

from .exceptions import (
    ClientError,
    InvalidInputError,
    NotFoundError,
    ServerError,
    UnauthorizedError,
)

# The API writes its error code at the start of the message, as in
# "not_found: product" or "forbidden"; only a few errors set extensions.code.
_CODE_PREFIX = re.compile(r"^([a-z][a-z0-9_]*)(?::\s*(.*))?$", re.DOTALL)

_SERVER_FAILURE = "An unexpected error occurred"

_READ_ACCESS_HINT = (
    "You do not have access to this workspace or product. "
    "Access is determined by your role (ADMIN, EDITOR, VIEWER, or NO_ACCESS). "
    "Contact your administrator if you need access."
)
_WRITE_ACCESS_HINT = (
    "Write operations require ADMIN or EDITOR role for the workspace or product. "
    "Users with VIEWER role can only read data."
)
_INPUT_HINTS = {
    "invalid_date_format": "Date must be in ISO 8601 format: YYYY-MM-DD.",
    "invalid_status_value": "Status must be one of: DRAFT, UNDER_REVIEW, DONE.",
}


def raise_for_errors(payload: dict[str, Any], *, write: bool = False) -> None:
    """Raise the SDK exception for the first error in an API response.

    Args:
        payload: The decoded response body.
        write: Whether the request changes data; picks the access hint.

    Raises:
        NotFoundError: The requested object does not exist.
        UnauthorizedError: The caller's role does not allow the request.
        InvalidInputError: A value sent by the caller was rejected.
        ServerError: The API failed while handling the request.
        ClientError: Any other rejected request.
    """
    errors = payload.get("errors")
    if not errors:
        return

    error = errors[0]
    message = str(error.get("message") or "").strip()
    code = (error.get("extensions") or {}).get("code")
    detail = message
    match = _CODE_PREFIX.match(message)
    if match:
        code = code or match.group(1)
        detail = (match.group(2) or "").strip()

    if code == "not_found" or (code or "").endswith("_not_found"):
        if match:
            subject = detail or code.removesuffix("not_found").replace("_", " ").strip() or "object"
            text = _sentence(f"{subject} not found")
        else:
            text = message
        raise NotFoundError(404, message=text, error_code=code)

    if code in ("forbidden", "missing_org"):
        hint = _WRITE_ACCESS_HINT if write else _READ_ACCESS_HINT
        reason = f"Access denied: {detail}." if detail else "Access denied."
        raise UnauthorizedError(403, message=f"{reason} {hint}", error_code=code)

    if code in _INPUT_HINTS or (code or "").startswith("invalid_") or message.startswith("Variable '$"):
        label = _INPUT_HINTS.get(code) or (_sentence(code) if code else "Invalid input.")
        raise InvalidInputError(400, message=f"{label} {detail}".strip(), error_code=code)

    if message == _SERVER_FAILURE:
        raise ServerError(500, message="The Poelis API failed to handle the request.", error_code=code)

    if "path" not in error:
        # The request itself was rejected before running, which means this SDK
        # version asks for something the API no longer offers.
        raise ClientError(
            400,
            message=(
                "This version of poelis-sdk is not compatible with the Poelis API. "
                f"Upgrade with `pip install -U poelis-sdk`. Details: {message}"
            ),
            error_code=code,
        )

    raise ClientError(400, message=f"The Poelis API rejected the request: {message}", error_code=code)


def _sentence(text: str) -> str:
    """Turn "invalid_property_type" or "product not found" into a sentence."""
    text = text.replace("_", " ")
    return f"{text[0].upper()}{text[1:]}."
