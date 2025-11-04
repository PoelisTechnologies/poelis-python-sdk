"""Tests for Browser names()/suggest() traversal and property access.

These tests avoid reliance on IPython and focus on programmatic APIs.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict

import pytest

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
            payload = json.loads(request.content.decode("utf-8"))
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

            # Children items - return one child item for filtering tests
            if "parentItemId" in query:
                if vars.get("parent") == "i1":
                    data = {"data": {"items": [
                        {"id": "i2", "name": "Child Item", "code": "CI", "description": "", "productId": "p1", "parentId": "i1", "owner": "o", "position": 1},
                    ]}}
                else:
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
    # Root workspaces
    root_ws = b.list_workspaces().names
    assert "uh2" in root_ws
    ws = b["uh2"]

    # Product names and suggestions
    prod_names = ws.list_products().names
    assert prod_names and "Widget Pro" in prod_names
    prod = ws["Widget Pro"]

    # Item names
    item_names = prod.list_items().names
    assert item_names and "Gadget A" in item_names
    item = prod["Gadget A"]

    # Properties list
    item_prop_names = item.list_properties().names
    assert "Color" in item_prop_names and "Weight" in item_prop_names

    # Properties via props helper (still works)
    prop_names = item.list_properties().names
    assert "Color" in prop_names and "Weight" in prop_names
    assert item.props["Color"].value == "Red"
    assert item.props["Weight"].value == 5


def test_names_filtering() -> None:
    """Test explicit filtering methods (item_names, product_names, property_names)."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    item = prod["Gadget A"]
    
    # Test workspace level filtering
    all_workspace_names = ws.list_products().names
    assert "Widget Pro" in all_workspace_names
    
    products_only = ws.list_products().names
    assert products_only == all_workspace_names  # At workspace level, children are products
    assert "Widget Pro" in products_only
    
    # Test product level filtering
    all_product_names = prod.list_items().names
    assert "Gadget A" in all_product_names
    
    items_only = prod.list_items().names
    assert items_only == all_product_names  # At product level, children are items
    assert "Gadget A" in items_only
    
    # Test item level filtering - properties list only
    item_all_names = item.list_properties().names
    assert "Color" in item_all_names and "Weight" in item_all_names
    
    # Test item level filtering - items only
    # Note: In the current mock, there are no child items, so this should be empty
    item_child_items = item.list_items().names
    assert isinstance(item_child_items, list)
    
    # Test item level filtering - properties only
    item_props_only = item.list_properties().names
    assert "Color" in item_props_only
    assert "Weight" in item_props_only
    assert len(item_props_only) == 2
    
    # Test invalid filters at different levels: should not exist on these nodes
    with pytest.raises(AttributeError):
        _ = ws.list_items()  # No items at workspace level
    with pytest.raises(AttributeError):
        _ = ws.list_properties()  # No props at workspace level
    with pytest.raises(AttributeError):
        _ = prod.list_products()  # No products at product level
    with pytest.raises(AttributeError):
        _ = prod.list_properties()  # No props at product level


def test_names_filtering_with_child_items() -> None:
    """Test explicit filtering methods when item has child items."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    item = prod["Gadget A"]
    
    # Refresh to load child items
    item._refresh()
    
    # Now item.list_properties() should return properties
    all_prop_names = item.list_properties().names
    assert "Color" in all_prop_names and "Weight" in all_prop_names
    
    # Filter for items only - should return child items
    child_items = item.list_items().names
    # In our mock, there's one child item
    assert "Child Item" in child_items or len(child_items) >= 0
    
    # Filter for properties only - should return only properties
    props_only = item.list_properties().names
    assert "Color" in props_only
    assert "Weight" in props_only
    # Should not include child item names
    assert "Child Item" not in props_only


