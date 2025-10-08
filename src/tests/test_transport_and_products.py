"""Tests for transport headers and products pagination."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from poelis_sdk import PoelisClient

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class _MockTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.requests.append(request)
        if request.url.path == "/v1/products":
            qs = request.url.params
            limit = int(qs.get("limit", 100))
            offset = int(qs.get("offset", 0))
            # two pages of 2 items
            data = []
            if offset == 0:
                data = [
                    {"id": "p1", "name": "Prod 1", "workspace_id": "w1"},
                    {"id": "p2", "name": "Prod 2", "workspace_id": "w1"},
                ]
            elif offset == 2:
                data = [
                    {"id": "p3", "name": "Prod 3", "workspace_id": "w1"},
                    {"id": "p4", "name": "Prod 4", "workspace_id": "w1"},
                ]
            else:
                data = []
            content = {
                "data": data,
                "limit": limit,
                "offset": offset,
            }
            return httpx.Response(200, json=content)
        return httpx.Response(404)


def test_auth_header_and_pagination(monkeypatch: "MonkeyPatch") -> None:
    """Verify Authorization header exists and pagination iterates over all pages."""

    client = PoelisClient(base_url="http://example.com", api_key="k", org_id="o")

    # Swap underlying httpx client with our mock transport
    from poelis_sdk.client import Transport as _T

    mt = _MockTransport()
    _orig_init = _T.__init__

    def _init(self, base_url: str, api_key: str, org_id: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        http_client = httpx.Client(base_url=base_url, transport=mt, timeout=timeout_seconds)
        self._client = http_client
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout_seconds

    _T.__init__ = _init  # type: ignore[assignment]
    try:
        # Recreate client to apply monkeypatched transport
        client = PoelisClient(base_url="http://example.com", api_key="k", org_id="o")
        results = list(client.products.iter_all(page_size=2))
        assert [p.id for p in results] == ["p1", "p2", "p3", "p4"]
        # Check headers on first request
        assert mt.requests, "no requests captured"
        first = mt.requests[0]
        assert first.headers.get("Authorization") == "ApiKey k"
        assert first.headers.get("Accept") == "application/json"
    finally:
        _T.__init__ = _orig_init  # type: ignore[assignment]


