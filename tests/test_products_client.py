"""Tests for ProductsClient list and version queries."""

from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        payload = json.loads(request.content.decode("utf-8"))
        query = payload.get("query", "")

        if "productVersions(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "productVersions": [
                            {
                                "productId": "p1",
                                "versionNumber": 2,
                                "title": "v2",
                                "description": "Ship",
                                "createdAt": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                },
                request=request,
            )

        if "products(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "products": [
                            {
                                "id": "p1",
                                "name": "Widget",
                                "description": None,
                                "readableId": "widget",
                                "workspaceId": "w1",
                                "baselineVersionNumber": 2,
                                "reviewers": [],
                            }
                        ]
                    }
                },
                request=request,
            )

        return httpx.Response(200, json={"data": {}}, request=request)


def test_list_by_workspace_parses_products() -> None:
    t = _Transport()
    c = client_with_transport(t)
    page = c.products.list_by_workspace(workspace_id="w1", q="wid", limit=5, offset=0)
    assert page.data[0].id == "p1"
    assert page.data[0].baseline_version_number == 2
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables["ws"] == "w1"
    assert variables["filter"] == {"q": "wid"}
    assert variables["limit"] == 5


def test_list_product_versions_parses_versions() -> None:
    t = _Transport()
    c = client_with_transport(t)
    page = c.products.list_product_versions(product_id="p1", limit=50, offset=0)
    assert len(page.data) == 1
    assert page.data[0].version_number == 2
    assert page.data[0].title == "v2"
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {"pid": "p1"}
