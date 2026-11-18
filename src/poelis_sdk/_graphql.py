"""Shared handling of GraphQL error responses."""

from __future__ import annotations

from typing import Any

from .exceptions import GraphQLError


def raise_for_graphql_errors(payload: dict[str, Any]) -> None:
    """Raise ``GraphQLError`` when a GraphQL response carries an ``errors`` key."""
    if "errors" in payload:
        raise GraphQLError(payload["errors"])
