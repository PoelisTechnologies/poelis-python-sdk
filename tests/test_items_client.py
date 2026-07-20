"""Tests for ItemsClient list/get and iterator behavior."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from poelis_sdk import PoelisClient

if TYPE_CHECKING:
    pass


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        if request.method == "POST" and request.url.path == "/v1/graphql":
            payload = json.loads(request.content.decode("utf-8"))
            query: str = payload.get("query", "")
            vars = payload.get("variables", {})

            if "items(productId:" in query:
                offset = int(vars.get("offset", 0))
                product_id = vars.get("pid")
                data = []
                if product_id == "p" and offset == 0:
                    data = [
                        {"id": "i1", "name": "Item 1", "readableId": "item_1", "productId": "p", "parentId": None, "position": 1},
                        {"id": "i2", "name": "Item 2", "readableId": "item_2", "productId": "p", "parentId": None, "position": 2},
                    ]
                elif product_id == "p" and offset == 2:
                    data = [
                        {"id": "i3", "name": "Item 3", "readableId": "item_3", "productId": "p", "parentId": None, "position": 3},
                    ]
                return httpx.Response(200, json={"data": {"items": data}}, request=request)

            if "item(id:" in query:
                item_id = vars.get("id")
                if item_id == "i1":
                    return httpx.Response(
                        200,
                        json={"data": {"item": {"id": "i1", "name": "Item 1", "readableId": "item_1", "productId": "p", "parentId": None, "position": 1}}},
                        request=request,
                    )
                return httpx.Response(200, json={"data": {"item": None}}, request=request)

            return httpx.Response(200, json={"data": {}}, request=request)

        return httpx.Response(404, request=request)


def _client_with_transport(t: httpx.BaseTransport) -> PoelisClient:
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k")
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_items_list_and_get() -> None:
    t = _Transport()
    c = _client_with_transport(t)
    items = c.items.list_by_product(product_id="p", limit=2, offset=0)
    assert [item["id"] for item in items] == ["i1", "i2"]
    payload = json.loads(t.calls[0].content.decode("utf-8"))
    assert payload["variables"]["limit"] == 2
    assert payload["variables"]["offset"] == 0
    assert payload["variables"]["pid"] == "p"
    item = c.items.get("i1")
    assert item["id"] == "i1"


def test_items_iter_all() -> None:
    t = _Transport()
    c = _client_with_transport(t)
    ids = [it["id"] for it in c.items.iter_all_by_product(product_id="p", page_size=2)]
    assert ids == ["i1", "i2", "i3"]
