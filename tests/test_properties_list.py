"""Tests for PropertiesClient.list (draft, numbered version and baseline reads)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from tests.conftest import client_with_transport

_ROWS = [
    {"__typename": "SdkNumericProperty", "id": "pn1", "name": "Mass", "numericValue": "12.5"},
    {"__typename": "SdkTextProperty", "id": "pt1", "name": "Notes", "value": "ok"},
]


class _Transport(httpx.BaseTransport):
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body
        self.requests: list[dict[str, Any]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.requests.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json=self._body, request=request)


@pytest.mark.parametrize(
    ("kwargs", "expected_version", "expected_include_deleted"),
    [
        ({}, None, False),
        ({"version": 3}, 3, False),
        ({"version": 0}, 0, False),
        ({"version": "baseline"}, "baseline", False),
        ({"version": " Baseline "}, "baseline", False),
        ({"include_deleted": True}, None, True),
    ],
)
def test_list_sends_version_and_include_deleted(
    kwargs: dict[str, Any], expected_version: Any, expected_include_deleted: bool
) -> None:
    transport = _Transport({"data": {"sdkProperties": _ROWS}})
    client = client_with_transport(transport)

    rows = client.properties.list("item-1", **kwargs)

    assert rows == _ROWS
    assert len(transport.requests) == 1
    sent = transport.requests[0]
    assert sent["variables"] == {
        "itemId": "item-1",
        "version": expected_version,
        "includeDeleted": expected_include_deleted,
    }


@pytest.mark.parametrize("version", ["latest", "3", "", -1, True, 2.5])
def test_list_rejects_an_invalid_version_before_any_request(version: Any) -> None:
    transport = _Transport({"data": {"sdkProperties": []}})
    client = client_with_transport(transport)

    with pytest.raises(ValueError, match="version must be"):
        client.properties.list("item-1", version=version)
    assert transport.requests == []


@pytest.mark.parametrize("body", [{"data": {"sdkProperties": None}}, {"data": None}])
def test_list_returns_empty_when_backend_returns_null(body: dict[str, Any]) -> None:
    client = client_with_transport(_Transport(body))

    assert client.properties.list("item-1", version="baseline") == []


def test_list_raises_graphql_errors_with_their_message() -> None:
    body = {"errors": [{"message": "Item not accessible"}], "data": None}
    client = client_with_transport(_Transport(body))

    with pytest.raises(RuntimeError, match="Item not accessible"):
        client.properties.list("item-1")
