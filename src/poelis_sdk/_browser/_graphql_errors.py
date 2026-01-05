"""GraphQL error mapping helpers for the Browser DSL.

This module is internal and mirrors logic currently implemented in
`poelis_sdk.browser` to keep behavior stable during refactors.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import NotFoundError, UnauthorizedError


def handle_graphql_read_errors(errors: list[dict[str, Any]]) -> None:
    """Handle GraphQL errors for read operations and map them to SDK exceptions.

    This function intentionally preserves the exception types and message
    behavior expected by the existing Browser implementation.

    Args:
        errors: List of GraphQL error dictionaries (as returned under the
            top-level `"errors"` key).

    Raises:
        NotFoundError: For `"not_found"` errors.
        UnauthorizedError: For `"forbidden"` errors (access denied).
        RuntimeError: For other errors.
    """

    if not errors:
        return

    error = errors[0]  # Use first error (behavior preserved)
    error_code = error.get("extensions", {}).get("code")
    error_message = error.get("message", "GraphQL error")

    if error_code == "not_found":
        raise NotFoundError(404, message=error_message)
    if error_code == "forbidden":
        enhanced_message = (
            f"{error_message}. "
            "You do not have access to this workspace or product. "
            "Access is determined by your role (EDITOR, VIEWER, or NO_ACCESS). "
            "Contact your administrator if you need access."
        )
        raise UnauthorizedError(403, message=enhanced_message)

    raise RuntimeError(f"GraphQL error: {error_message}")


# Backwards-compatible alias for the existing internal helper name used in
# `poelis_sdk.browser`. This keeps the moved code changes purely structural.
_handle_graphql_read_errors = handle_graphql_read_errors


