"""GraphQL error responses raise GraphQLError, which is still a RuntimeError."""

from __future__ import annotations

from typing import Any, Callable

import httpx
import pytest

from poelis_sdk import PoelisClient
from poelis_sdk.exceptions import GraphQLError, NotFoundError, PoelisError, UnauthorizedError

from tests.conftest import client_with_transport

ERRORS = [{"message": "boom", "extensions": {"code": "internal_error"}}]


class _ErrorTransport(httpx.BaseTransport):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self._errors = errors

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": None, "errors": self._errors})


CALLS: dict[str, Callable[[PoelisClient], Any]] = {
    "items.list_by_product": lambda c: c.items.list_by_product(product_id="p1"),
    "items.get": lambda c: c.items.get("i1"),
    "products.list_by_workspace": lambda c: c.products.list_by_workspace(workspace_id="w1"),
    "products.list_product_versions": lambda c: c.products.list_product_versions(product_id="p1"),
    "products.set_product_baseline_version": lambda c: c.products.set_product_baseline_version(
        product_id="p1", version_number=1
    ),
    "search.products": lambda c: c.search.products(q="x", workspace_id="w1"),
    "search.items": lambda c: c.search.items(q="x", product_id="p1"),
    "search.properties": lambda c: c.search.properties(q="x"),
    "versions.list_items": lambda c: c.versions.list_items(product_id="p1", version_number=1),
    "workspaces.list": lambda c: c.workspaces.list(),
    "workspaces.get": lambda c: c.workspaces.get(workspace_id="w1"),
    "workspaces.get_user_accessible_resources": lambda c: c.workspaces.get_user_accessible_resources(
        user_id="u1"
    ),
    "properties.update_numeric_property": lambda c: c.properties.update_numeric_property(
        id="pr1", value="1"
    ),
}


@pytest.mark.parametrize("call", CALLS.values(), ids=CALLS.keys())
def test_graphql_errors_raise_graphql_error(call: Callable[[PoelisClient], Any]) -> None:
    client = client_with_transport(_ErrorTransport(ERRORS))

    with pytest.raises(GraphQLError) as exc_info:
        call(client)

    assert isinstance(exc_info.value, RuntimeError)
    assert isinstance(exc_info.value, PoelisError)
    assert exc_info.value.errors == ERRORS
    assert exc_info.value.code == "internal_error"


def test_graphql_error_keeps_the_previous_message() -> None:
    client = client_with_transport(_ErrorTransport(ERRORS))

    with pytest.raises(GraphQLError, match="boom") as exc_info:
        client.workspaces.list()

    assert str(exc_info.value) == str(ERRORS)


@pytest.mark.parametrize(
    ("code", "expected"),
    [("not_found", NotFoundError), ("forbidden", UnauthorizedError)],
)
def test_property_updates_keep_their_specific_error_codes(code: str, expected: type[Exception]) -> None:
    client = client_with_transport(_ErrorTransport([{"message": "no", "extensions": {"code": code}}]))

    with pytest.raises(expected):
        client.properties.update_numeric_property(id="pr1", value="1")
