"""Tests for Browser names()/suggest() traversal and property access.

These tests avoid reliance on IPython and focus on programmatic APIs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import httpx

from poelis_sdk import PoelisClient

if TYPE_CHECKING:
    pass


class _MockTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.requests.append(request)
        if request.method == "POST" and request.url.path == "/v1/graphql":
            payload = request.json()  # type: ignore[no-untyped-call]
            query: str = payload.get("query", "")
            vars: Dict[str, Any] = payload.get("variables", {})

            # Workspaces
            if "workspaces(" in query:
                data = {"data": {"workspaces": [
                    {"id": "w1", "orgId": "o", "name": "uh2", "projectLimit": 10},
                ]}}
                return httpx.Response(200, json=data)

            # Products by workspace
            if "products(" in query:
                assert vars.get("ws") == "w1"
                data = {"data": {"products": [
                    {"id": "p1", "name": "Widget Pro", "workspaceId": "w1", "code": "WP", "description": ""},
                ]}}
                return httpx.Response(200, json=data)

            # Items by product (top-level only)
            if "items(productId:" in query and "parentItemId" not in query:
                assert vars.get("pid") == "p1"
                data = {"data": {"items": [
                    {"id": "i1", "name": "Gadget A", "code": "GA", "description": "", "productId": "p1", "parentId": None, "owner": "o", "position": 1},
                ]}}
                return httpx.Response(200, json=data)

            # Children items (none)
            if "parentItemId" in query:
                data = {"data": {"items": []}}
                return httpx.Response(200, json=data)

            # Properties for item
            if query.strip().startswith("query($iid: ID!) {\n  properties"):
                assert vars.get("iid") == "i1"
                data = {"data": {"properties": [
                    {"__typename": "TextProperty", "name": "Color", "value": "Red"},
                    {"__typename": "NumericProperty", "name": "Weight", "integerPart": 5, "exponent": 0, "category": "Mass"},
                ]}}
                return httpx.Response(200, json=data)

            return httpx.Response(200, json={"data": {}})

        return httpx.Response(404)


def _client_with_graphql_mock(t: httpx.BaseTransport) -> PoelisClient:
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, org_id: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout_seconds

        # minimal stubs for headers used by transport
        class _Auth0:
            def __init__(self) -> None:
                pass

            def get_token(self) -> str:
                return "tok"

        self._auth0_manager = _Auth0()

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", org_id="o")
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_browser_traversal_and_properties() -> None:
    """End-to-end traversal: workspace → product → item → property value."""

    t = _MockTransport()
    c = _client_with_graphql_mock(t)

    b = c.browser
    # Root suggestions and names
    root_suggest = b.suggest()
    assert "uh2" in root_suggest or "uh2" in [s for s in root_suggest]
    ws = b["uh2"]

    # Product names and suggestions
    prod_names = ws.names()
    assert prod_names and "Widget Pro" in prod_names
    prod = ws["Widget Pro"]

    # Item names
    item_names = prod.names()
    assert item_names and "Gadget A" in item_names
    item = prod["Gadget A"]

    # Properties via props helper
    prop_names = item.props.names()
    assert "Color" in prop_names and "Weight" in prop_names
    assert item.props["Color"].value == "Red"
    assert item.props["Weight"].value == 5


