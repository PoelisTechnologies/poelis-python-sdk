"""Tests for ItemsClient list/get and iterator behavior."""

from __future__ import annotations

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
        if request.method == "GET" and request.url.path == "/v1/items":
            params = request.url.params
            limit = int(params.get("limit", 100))
            offset = int(params.get("offset", 0))
            product_id = params.get("product_id")
            data = []
            if product_id == "p" and offset == 0:
                data = [{"id": "i1"}, {"id": "i2"}]
            elif product_id == "p" and offset == 2:
                data = [{"id": "i3"}]
            content = {"data": data, "limit": limit, "offset": offset}
            return httpx.Response(200, json=content)
        if request.method == "GET" and request.url.path == "/v1/items/i1":
            return httpx.Response(200, json={"id": "i1", "name": "Item 1"})
        return httpx.Response(404)


def _client_with_transport(t: httpx.BaseTransport) -> PoelisClient:
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, org_id: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", org_id="o")
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_items_list_and_get() -> None:
    t = _Transport()
    c = _client_with_transport(t)
    page = c.items.list(product_id="p", limit=2, offset=0)
    assert page["limit"] == 2 and page["offset"] == 0
    item = c.items.get("i1")
    assert item["id"] == "i1"


def test_items_iter_all() -> None:
    t = _Transport()
    c = _client_with_transport(t)
    ids = [it["id"] for it in c.items.iter_all(product_id="p", page_size=2)]
    assert ids == ["i1", "i2", "i3"]


