"""Tests for low-level version item listing behavior."""

from __future__ import annotations

import json
from typing import Any

import httpx

from poelis_sdk import PoelisClient


class _MockTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.queries: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.requests.append(request)
        if request.method == "POST" and request.url.path == "/v1/graphql":
            payload = json.loads(request.content.decode("utf-8"))
            query = payload.get("query", "")
            self.queries.append(query)
            if "sdkItems(" in query:
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "sdkItems": [
                                {
                                    "id": "i1",
                                    "name": "Active Item",
                                    "readableId": "active_item",
                                    "productId": "p1",
                                    "parentId": None,
                                    "position": 1,
                                    "deleted": False,
                                },
                                {
                                    "id": "i2",
                                    "name": "Deleted Item",
                                    "readableId": "deleted_item",
                                    "productId": "p1",
                                    "parentId": None,
                                    "position": 2,
                                    "deleted": True,
                                },
                            ]
                        }
                    },
                )
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(404)


def _client_with_transport(t: httpx.BaseTransport) -> PoelisClient:
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, timeout_seconds: float, **_: Any) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", enable_change_detection=False)
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_versions_list_items_returns_deleted_rows_without_filtering() -> None:
    t = _MockTransport()
    c = _client_with_transport(t)

    rows = c.versions.list_items(product_id="p1", version_number=5)

    assert [row["readableId"] for row in rows] == ["active_item", "deleted_item"]
    assert rows[0]["deleted"] is False
    assert rows[1]["deleted"] is True
    assert t.queries and any("deleted" in query for query in t.queries)
