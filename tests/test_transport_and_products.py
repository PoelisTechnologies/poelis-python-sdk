"""Tests for transport headers and products pagination."""

from __future__ import annotations

import json
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
        if request.url.path != "/v1/graphql":
            return httpx.Response(404, request=request)

        body = json.loads(request.content.decode())
        query = body.get("query", "")
        variables = body.get("variables", {})

        if "workspaces(limit:" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "workspaces": [
                            {"id": "w1", "orgId": "o1", "name": "Workspace 1", "readableId": "workspace_1"}
                        ]
                    }
                },
                request=request,
            )

        if "products(workspaceId:" in query:
            all_products = [
                {
                    "id": "p1",
                    "name": "Prod 1",
                    "readableId": "P-1",
                    "workspaceId": "w1",
                    "baselineVersionNumber": 1,
                    "reviewers": [],
                },
                {
                    "id": "p2",
                    "name": "Prod 2",
                    "readableId": "P-2",
                    "workspaceId": "w1",
                    "baselineVersionNumber": None,
                    "reviewers": [],
                },
                {
                    "id": "p3",
                    "name": "Prod 3",
                    "readableId": "P-3",
                    "workspaceId": "w1",
                    "baselineVersionNumber": 3,
                    "reviewers": [],
                },
                {
                    "id": "p4",
                    "name": "Prod 4",
                    "readableId": "P-4",
                    "workspaceId": "w1",
                    "baselineVersionNumber": None,
                    "reviewers": [],
                },
            ]
            if variables.get("ws") != "w1":
                page = []
            else:
                limit = int(variables.get("limit", 100))
                offset = int(variables.get("offset", 0))
                page = all_products[offset:offset + limit]
            return httpx.Response(
                200,
                json={"data": {"products": page}},
                request=request,
            )

        if "SetBaseline" in query and "setProductBaselineVersion" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "setProductBaselineVersion": {
                            "id": "p1",
                            "name": "Prod 1",
                            "readableId": "P-1",
                            "workspaceId": "w1",
                            "baselineVersionNumber": 5,
                            "reviewers": [],
                        }
                    }
                },
                request=request,
            )

        return httpx.Response(404, request=request)


def test_auth_header_and_pagination(monkeypatch: "MonkeyPatch") -> None:
    """Verify auth headers exist and pagination iterates over all pages."""

    client = PoelisClient(base_url="http://example.com", api_key="k")

    # Swap underlying httpx client with our mock transport
    from poelis_sdk.client import Transport as _T

    mt = _MockTransport()
    _orig_init = _T.__init__

    def _init(self, base_url: str, api_key: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        http_client = httpx.Client(base_url=base_url, transport=mt, timeout=timeout_seconds)
        self._client = http_client
        self._api_key = api_key
        self._timeout = timeout_seconds

    _T.__init__ = _init  # type: ignore[assignment]
    try:
        # Recreate client to apply monkeypatched transport
        client = PoelisClient(base_url="http://example.com", api_key="k")
        results = list(client.products.iter_all(page_size=2))
        assert [p.id for p in results] == ["p1", "p2", "p3", "p4"]
        # Baseline version numbers are exposed on the Product model
        assert [p.baseline_version_number for p in results] == [1, None, 3, None]
        # Check headers on first request
        assert mt.requests, "no requests captured"
        first = mt.requests[0]
        # Default auth mode is Authorization: Bearer
        assert first.headers.get("Authorization") == "Bearer k"
        assert first.headers.get("Accept") == "application/json"

        # Verify that the baseline mutation helper issues a GraphQL request and parses the response
        updated = client.products.set_product_baseline_version(product_id="p1", version_number=5)
        assert updated.id == "p1"
        assert updated.baseline_version_number == 5
        assert updated.readableId == "P-1"
    finally:
        _T.__init__ = _orig_init  # type: ignore[assignment]

