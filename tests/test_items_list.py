"""items.list and items.iter_all read items in the draft or at a version."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from poelis_sdk.models import Item

from tests.conftest import client_with_transport


def _row(
    item_id: str,
    *,
    parent: str | None = None,
    parent_draft: str | None = None,
    draft: str | None = None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "readableId": f"key_{item_id}",
        "productId": "p1",
        "parentId": parent,
        "parentDraftItemId": parent_draft,
        "name": f"Item {item_id}",
        "description": None,
        "partNumber": None,
        "draftItemId": draft,
        "deleted": False,
        "position": 1.0,
    }


class _ItemsTransport(httpx.BaseTransport):
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.requests: list[dict[str, Any]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        variables = body["variables"]
        offset, limit = variables["offset"], variables["limit"]
        return httpx.Response(200, json={"data": {"sdkItems": self.rows[offset : offset + limit]}})


@pytest.mark.parametrize(
    ("version", "sent"),
    [(None, None), (3, 3), ("baseline", "baseline"), ("Baseline", "baseline")],
)
def test_list_sends_the_version(version: int | str | None, sent: int | str | None) -> None:
    transport = _ItemsTransport([_row("i1")])
    client = client_with_transport(transport)

    client.items.list("p1", version=version)

    request = transport.requests[0]
    assert "query SdkListItemsAtVersion" in request["query"]
    assert request["variables"]["pid"] == "p1"
    assert request["variables"]["version"] == sent


def test_list_returns_both_parent_ids() -> None:
    transport = _ItemsTransport([_row("v2", parent="snap-1", parent_draft="d1", draft="d2")])
    client = client_with_transport(transport)

    [item] = client.items.list("p1", version=1)

    assert isinstance(item, Item)
    assert item.id == "v2"
    assert item.key == "key_v2"
    assert item.product_id == "p1"
    assert item.parent_item_id == "snap-1"
    assert item.parent_draft_item_id == "d1"
    assert item.draft_item_id == "d2"


def test_list_sends_filters_and_page() -> None:
    transport = _ItemsTransport([])
    client = client_with_transport(transport)

    client.items.list("p1", q="bolt", root_only=True, include_deleted=True, limit=5, offset=10)

    variables = transport.requests[0]["variables"]
    assert variables["filter"] == {"q": "bolt", "rootOnly": True, "includeDeleted": True}
    assert (variables["limit"], variables["offset"]) == (5, 10)


def test_iter_all_walks_every_page_from_start_offset() -> None:
    transport = _ItemsTransport([_row(f"i{n}") for n in range(5)])
    client = client_with_transport(transport)

    ids = [item.id for item in client.items.iter_all("p1", version=2, page_size=2, start_offset=1)]

    assert ids == ["i1", "i2", "i3", "i4"]
    assert [r["variables"]["offset"] for r in transport.requests] == [1, 3, 5]


@pytest.mark.parametrize("version", [-1, True, "latest", 1.5])
def test_list_rejects_invalid_versions(version: Any) -> None:
    client = client_with_transport(_ItemsTransport([]))

    with pytest.raises(ValueError):
        client.items.list("p1", version=version)


def test_list_raises_on_graphql_errors() -> None:
    class _Errors(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"errors": [{"message": "boom"}]})

    client = client_with_transport(_Errors())

    with pytest.raises(RuntimeError, match="boom"):
        client.items.list("p1")
