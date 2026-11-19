"""API error responses raise SDK exceptions that describe the problem."""

from __future__ import annotations

from typing import Any, Callable

import httpx
import pytest

from poelis_sdk import PoelisClient
from poelis_sdk._api_errors import raise_for_errors
from poelis_sdk.exceptions import (
    ClientError,
    HTTPError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
    PoelisError,
    ServerError,
    UnauthorizedError,
)
from tests.conftest import client_with_transport


def _error(message: str, code: str | None = None, *, path: bool = True) -> dict[str, Any]:
    error: dict[str, Any] = {"message": message, "locations": [{"line": 2, "column": 3}]}
    if path:
        error["path"] = ["field"]
    if code:
        error["extensions"] = {"code": code}
    return error


@pytest.mark.parametrize(
    ("error", "expected", "code", "message"),
    [
        (_error("not_found: product"), NotFoundError, "not_found", "Product not found."),
        (_error("workspace_not_found"), NotFoundError, "workspace_not_found", "Workspace not found."),
        (_error("not_found"), NotFoundError, "not_found", "Object not found."),
        (_error("Item i1 does not exist", "not_found"), NotFoundError, "not_found", "Item i1 does not exist"),
        (_error("forbidden"), UnauthorizedError, "forbidden", "Access denied."),
        (_error("missing_org"), UnauthorizedError, "missing_org", "Access denied."),
        (
            _error("forbidden: can only update draft properties"),
            UnauthorizedError,
            "forbidden",
            "Access denied: can only update draft properties.",
        ),
        (
            _error("invalid_property_type: TEXT"),
            InvalidInputError,
            "invalid_property_type",
            "Invalid property type. TEXT",
        ),
        (
            _error("bad date", "invalid_date_format"),
            InvalidInputError,
            "invalid_date_format",
            "Date must be in ISO 8601 format: YYYY-MM-DD. bad date",
        ),
        (
            _error("Variable '$id' got invalid value 1", path=False),
            InvalidInputError,
            None,
            "Invalid input. Variable '$id' got invalid value 1",
        ),
        (
            _error("An unexpected error occurred"),
            ServerError,
            None,
            "The Poelis API failed to handle the request.",
        ),
        (
            _error("Cannot query field 'x' on type 'Item'.", path=False),
            ClientError,
            None,
            "This version of poelis-sdk is not compatible with the Poelis API.",
        ),
        (
            _error("value must be valid JSON array"),
            ClientError,
            None,
            "The Poelis API rejected the request: value must be valid JSON array",
        ),
    ],
)
def test_errors_map_to_sdk_exceptions(
    error: dict[str, Any], expected: type[HTTPError], code: str | None, message: str
) -> None:
    with pytest.raises(expected) as caught:
        raise_for_errors({"data": None, "errors": [error]})

    assert type(caught.value) is expected
    assert caught.value.error_code == code
    assert str(caught.value).startswith(message)
    assert isinstance(caught.value, RuntimeError)
    assert "graphql" not in str(caught.value).lower()
    assert "locations" not in str(caught.value)


def test_invalid_input_is_still_a_value_error() -> None:
    with pytest.raises(ValueError):
        raise_for_errors({"errors": [_error("invalid_status_value")]})


def test_access_hint_depends_on_whether_the_request_writes() -> None:
    with pytest.raises(UnauthorizedError, match="Contact your administrator"):
        raise_for_errors({"errors": [_error("forbidden")]})
    with pytest.raises(UnauthorizedError, match="require ADMIN or EDITOR"):
        raise_for_errors({"errors": [_error("forbidden")]}, write=True)


def test_a_response_without_errors_does_not_raise() -> None:
    raise_for_errors({"data": {"x": 1}})
    raise_for_errors({"data": {"x": 1}, "errors": []})


class _ErrorTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": None, "errors": [_error("not_found: product")]})


CALLS: dict[str, Callable[[PoelisClient], Any]] = {
    "items.list": lambda c: c.items.list("p1"),
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
    "files.list": lambda c: c.files.list(item_id="i1"),
    "properties.update_numeric_property": lambda c: c.properties.update_numeric_property(
        id="pr1", value="1"
    ),
}


@pytest.mark.parametrize("call", CALLS.values(), ids=CALLS.keys())
def test_every_method_raises_the_mapped_error(call: Callable[[PoelisClient], Any]) -> None:
    client = client_with_transport(_ErrorTransport())

    with pytest.raises(NotFoundError, match="Product not found.") as caught:
        call(client)

    assert caught.value.error_code == "not_found"


class _UnreachableTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)


def test_an_unreachable_api_raises_network_error() -> None:
    client = client_with_transport(_UnreachableTransport())

    with pytest.raises(NetworkError, match="Could not reach the Poelis API") as caught:
        client.workspaces.list()

    assert isinstance(caught.value, PoelisError)
    assert isinstance(caught.value, httpx.TransportError)
    assert isinstance(caught.value.__cause__, httpx.ConnectError)
