"""Tests for SearchClient endpoints alignment and basic params."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from poelis_sdk import PoelisClient

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class _MockTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        if request.url.path == "/v1/search/products":
            return httpx.Response(200, json={"hits": [], "limit": 20, "offset": 0})
        if request.url.path == "/v1/search/items":
            return httpx.Response(200, json={"hits": [], "limit": 20, "offset": 0})
        if request.url.path == "/v1/search/properties":
            return httpx.Response(200, json={"hits": [], "limit": 20, "offset": 0})
        return httpx.Response(404)


def test_search_endpoints(monkeypatch: "MonkeyPatch") -> None:
    from poelis_sdk.client import Transport as _T

    t = _MockTransport()

    def _init(self, base_url: str, api_key: str, org_id: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        c = PoelisClient(base_url="http://localhost:8000", api_key="k", org_id="o")
        assert c.search.products(q="abc")["hits"] == []
        assert c.search.items(q="abc")["hits"] == []
        assert c.search.properties(q="abc")["hits"] == []
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


