"""Tests for SearchClient: uses GraphQL /v1/graphql only."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from poelis_sdk import PoelisClient
from tests.conftest import client_with_transport

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class _MockTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        if request.url.path != "/v1/graphql" or request.method != "POST":
            return httpx.Response(404)
        body = request.content.decode()
        if "products(" in body:
            return httpx.Response(200, json={"data": {"products": []}})
        if "items(" in body:
            return httpx.Response(200, json={"data": {"items": []}})
        if "searchProperties(" in body:
            return httpx.Response(200, json={"data": {"searchProperties": {"query": "", "hits": [], "total": 0, "limit": 20, "offset": 0, "processingTimeMs": 0}}})
        return httpx.Response(404)


class _PropertiesSearchTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        if request.url.path != "/v1/graphql" or request.method != "POST":
            return httpx.Response(404)
        payload = json.loads(request.content.decode("utf-8"))
        query = payload.get("query", "")
        if "searchProperties(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "searchProperties": {
                            "query": "mass",
                            "hits": [
                                {
                                    "id": "prop-1",
                                    "workspaceId": "w1",
                                    "productId": "p1",
                                    "itemId": "i1",
                                    "propertyType": "numeric",
                                    "name": "Mass",
                                    "category": "MASS",
                                    "value": "12.5",
                                }
                            ],
                            "total": 1,
                            "limit": 5,
                            "offset": 0,
                            "processingTimeMs": 3,
                        }
                    }
                },
                request=request,
            )
        return httpx.Response(404, request=request)


def test_search_properties_passes_filters_and_parses_hits() -> None:
    t = _PropertiesSearchTransport()
    c = client_with_transport(t)
    result = c.search.properties(
        q="mass",
        workspace_id="w1",
        product_id="p1",
        item_id="i1",
        property_type="numeric",
        category="MASS",
        limit=5,
        offset=0,
        sort="updated_at",
    )
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {
        "q": "mass",
        "ws": "w1",
        "pid": "p1",
        "iid": "i1",
        "ptype": "numeric",
        "cat": "MASS",
        "limit": 5,
        "offset": 0,
        "sort": "updated_at",
    }
    hit = result["hits"][0]
    assert hit["id"] == "prop-1"
    assert hit["name"] == "Mass"
    assert hit["propertyType"] == "numeric"


def test_search_endpoints(monkeypatch: "MonkeyPatch") -> None:
    from poelis_sdk.client import Transport as _T

    t = _MockTransport()

    def _init(self, base_url: str, api_key: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        c = PoelisClient(base_url="http://localhost:8000", api_key="k")
        assert c.search.products(q="abc", workspace_id="ws1")["hits"] == []
        assert c.search.items(q="abc", product_id="pid1")["hits"] == []
        assert c.search.properties(q="abc")["hits"] == []
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


