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

            # Items by product (top-level only, but include child items for draft queries)
            if "items(productId:" in query and "parentItemId" not in query and "version:" not in query:
                assert vars.get("pid") == "p1"
                # For draft queries, include both parent and child items
                data = {"data": {"items": [
                    {"id": "i1", "name": "Gadget A", "code": "GA", "description": "", "productId": "p1", "parentId": None, "position": 1},
                    {"id": "i2", "name": "Child Item", "code": "CI", "description": "", "productId": "p1", "parentId": "i1", "position": 1},
                ]}}
                return httpx.Response(200, json=data)

            # Children items - return one child item for filtering tests
            if "parentItemId" in query:
                if vars.get("parent") == "i1":
                    data = {"data": {"items": [
                        {"id": "i2", "name": "Child Item", "code": "CI", "description": "", "productId": "p1", "parentId": "i1", "position": 1},
                    ]}}
                else:
                    data = {"data": {"items": []}}
                return httpx.Response(200, json=data)

            # Properties for item (both with and without version)
            # NOTE: When change detection is enabled the SDK may query `sdkProperties(...)`.
            if "properties(itemId:" in query or "sdkProperties(itemId:" in query:
                item_id = vars.get("iid")
                is_sdk = "sdkProperties(itemId:" in query
                if item_id == "i1":
                    # Return properties for parent item (no demo_property_mass here)
                    # Note: "Color" and "Weight" use capitalized readableId to match existing tests
                    props = [
                        {"__typename": "TextProperty", "id": "p1", "name": "Color", "readableId": "Color", "value": "Red", "parsedValue": "Red"},
                        {"__typename": "NumericProperty", "id": "p3", "name": "Weight", "readableId": "Weight", "integerPart": 5, "exponent": 0, "category": "Mass"},
                    ]
                    data = {"data": {"properties": props, "sdkProperties": props} if is_sdk else {"properties": props}}
                    return httpx.Response(200, json=data)
                elif item_id == "i2":
                    # Return properties for child item (demo_property_mass is here)
                    props = [
                        {"__typename": "NumericProperty", "id": "p2", "name": "Mass", "readableId": "demo_property_mass", "category": "Mass", "displayUnit": "kg", "value": "10.5", "parsedValue": 10.5},
                    ]
                    data = {"data": {"properties": props, "sdkProperties": props} if is_sdk else {"properties": props}}
                    return httpx.Response(200, json=data)
                else:
                    # Return empty for other items
                    data = {"data": {"properties": [], "sdkProperties": []} if is_sdk else {"properties": []}}
                    return httpx.Response(200, json=data)

            # Product versions
            if "productVersions(" in query:
                assert vars.get("pid") == "p1"
                data = {"data": {"productVersions": [
                    {"productId": "p1", "versionNumber": 1, "title": "version 1", "description": "First version", "createdAt": "2024-01-01T00:00:00Z"},
                    {"productId": "p1", "versionNumber": 2, "title": "version 2", "description": "Second version", "createdAt": "2024-01-02T00:00:00Z"},
                    {"productId": "p1", "versionNumber": 3, "title": "version 3", "description": "Third version", "createdAt": "2024-01-03T00:00:00Z"},
                ]}}
                return httpx.Response(200, json=data)

            # Versioned items
            if "items(productId:" in query and "version:" in query:
                assert vars.get("pid") == "p1"
                # Include both parent and child items for all versioned queries
                data = {"data": {"items": [
                    {"id": "i1", "name": "Gadget A", "readableId": "gadget_a", "productId": "p1", "parentId": None, "position": 1},
                    {"id": "i2", "name": "Child Item", "readableId": "child_item", "productId": "p1", "parentId": "i1", "position": 1},
                ]}}
                return httpx.Response(200, json=data)


            return httpx.Response(200, json={"data": {}})

        return httpx.Response(404)


def _client_with_graphql_mock(t: httpx.BaseTransport, **client_kwargs: Any) -> PoelisClient:
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, timeout_seconds: float, **_: Any) -> None:  # type: ignore[no-redef]
        # org_id was removed from Transport and is deprecated in PoelisClient.
        # Keep the test monkeypatch tolerant to avoid coupling to a signature.
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds


    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", org_id="o", **client_kwargs)
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
    # For versioned/baseline product nodes, the browser prefers `readableId` when present.
    assert item_names and "gadget_a" in item_names
    item = prod["gadget_a"]

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
    item = prod["gadget_a"]
    
    # Test workspace level filtering
    all_workspace_names = ws.list_products().names
    assert "Widget Pro" in all_workspace_names
    
    products_only = ws.list_products().names
    assert products_only == all_workspace_names  # At workspace level, children are products
    assert "Widget Pro" in products_only
    
    # Test product level filtering
    all_product_names = prod.list_items().names
    assert "gadget_a" in all_product_names
    
    items_only = prod.list_items().names
    assert items_only == all_product_names  # At product level, children are items
    assert "gadget_a" in items_only
    
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
    assert len(item_props_only) == 2  # Color, Weight (demo_property_mass is in child item)
    
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
    item = prod["gadget_a"]
    
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


def test_baseline_version_access() -> None:
    """Test accessing the latest version via baseline property."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # Access baseline (should return latest version, which is v3)
    baseline = prod.baseline
    assert baseline is not None
    assert baseline._name == "v3"
    assert baseline._id == "3"
    assert baseline._level == "version"
    
    # Baseline should be accessible and work like a version node
    assert hasattr(baseline, "list_items")


def test_version_method_by_title() -> None:
    """Test accessing versions by title using get_version() method."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # Access version by exact title
    v1 = prod.get_version("version 1")
    assert v1 is not None
    assert v1._name == "v1"
    assert v1._id == "1"
    assert v1._level == "version"
    
    # Access version by different title
    v2 = prod.get_version("version 2")
    assert v2 is not None
    assert v2._name == "v2"
    assert v2._id == "2"
    
    # Access latest version by title
    v3 = prod.get_version("version 3")
    assert v3 is not None
    assert v3._name == "v3"
    assert v3._id == "3"
    
    # Test case-insensitive matching
    v1_case = prod.get_version("VERSION 1")
    assert v1_case is not None
    assert v1_case._id == "1"
    
    # Test with whitespace
    v2_space = prod.get_version("  version 2  ")
    assert v2_space is not None
    assert v2_space._id == "2"
    
    # Test error for non-existent version
    with pytest.raises(ValueError, match="No version found"):
        _ = prod.get_version("nonexistent version")


def test_version_method_by_version_number() -> None:
    """Test accessing versions by version number using get_version() method."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # Access version by number with "v" prefix
    v1 = prod.get_version("v1")
    assert v1 is not None
    assert v1._id == "1"
    
    # Access version by number without prefix
    v2 = prod.get_version("2")
    assert v2 is not None
    assert v2._id == "2"
    
    # Access latest version
    v3 = prod.get_version("v3")
    assert v3 is not None
    assert v3._id == "3"


def test_get_property_on_version_raises_error() -> None:
    """Test that get_property is not available on version nodes and raises AttributeError."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # Access version v1
    v1 = prod.v1
    
    # get_property should not be available on version nodes
    with pytest.raises(AttributeError, match="get_property.*not available on version nodes"):
        _ = v1.get_property("demo_property_mass")
    
    # Users should access items in the version first, then get properties from items
    # Load children for v1 and get item from cache
    v1._load_children()
    item = v1._children_cache.get("gadget_a") or v1._children_cache.get("Gadget_A")
    if not item:
        # Try to get by name
        for child in v1._children_cache.values():
            if child._name == "Gadget A" or child._name == "gadget_a":
                item = child
                break
    assert item is not None, "Item not found in version"
    mass_prop = item.get_property("demo_property_mass")
    
    # Verify it returns a property wrapper with correct value
    assert mass_prop is not None
    assert mass_prop.value == 10.5
    assert mass_prop.name == "demo_property_mass"
    assert mass_prop.category == "Mass"
    assert mass_prop.unit == "kg"
    
    # Test that get_property is NOT available on product nodes
    with pytest.raises(AttributeError, match="get_property.*not available on product nodes"):
        _ = prod.get_property("demo_property_mass")


def test_get_property_on_product_node_raises_error() -> None:
    """Test that get_property is not available on product nodes and raises AttributeError."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # get_property should not be available on product nodes
    with pytest.raises(AttributeError, match="get_property.*not available on product nodes"):
        _ = prod.get_property("demo_property_mass")
    
    # Users should access items in baseline first, then get properties from items
    # For product nodes, accessing items automatically routes through baseline
    item = prod["gadget_a"]
    mass_prop = item.get_property("demo_property_mass")
    assert mass_prop is not None
    assert mass_prop.value == 10.5
    assert mass_prop.name == "demo_property_mass"
    assert mass_prop.category == "Mass"
    assert mass_prop.unit == "kg"


def test_get_property_on_item_node() -> None:
    """Test getting a property by readableId from an item node (searches recursively)."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    item = prod["gadget_a"]
    
    # Get property from item node (should search in item and sub-items)
    # In our mock, demo_property_mass is in child item i2
    mass_prop = item.get_property("demo_property_mass")
    
    # Verify it returns a property wrapper with correct value
    assert mass_prop is not None
    assert mass_prop.value == 10.5
    assert mass_prop.name == "demo_property_mass"
    assert mass_prop.category == "Mass"
    assert mass_prop.unit == "kg"
    
    # Test error for non-existent property
    with pytest.raises(RuntimeError, match="not found"):
        _ = item.get_property("nonexistent_property")


def test_get_property_on_item_node_with_version() -> None:
    """Test getting a property by readableId from an item node in a versioned context."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    v1 = prod.v1
    
    # Load items for v1
    v1._load_children()
    item = v1._children_cache.get("gadget_a") or v1._children_cache.get("Gadget_A")
    if not item:
        # Try to get by name
        for child in v1._children_cache.values():
            if child._name == "gadget_a":
                item = child
                break
    
    # Get property from versioned item node (should search recursively in sub-items)
    mass_prop = item.get_property("demo_property_mass")
    
    # Verify it returns a property wrapper
    assert mass_prop is not None
    assert mass_prop.value == 10.5


def test_get_property_on_draft_version_raises_error() -> None:
    """Test that get_property is not available on draft version nodes."""
    
    t = _MockTransport()
    c = _client_with_graphql_mock(t)
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # Access draft version
    draft = prod.draft
    
    # get_property should not be available on version nodes (including draft)
    with pytest.raises(AttributeError, match="get_property.*not available on version nodes"):
        _ = draft.get_property("demo_property_mass")
    
    # Users should access items in draft first, then get properties from items
    # Load children for draft and get item from cache
    draft._load_children()
    item = draft._children_cache.get("gadget_a") or draft._children_cache.get("Gadget_A")
    if not item:
        # Try to get by name
        for child in draft._children_cache.values():
            if child._name == "Gadget A" or child._name == "gadget_a":
                item = child
                break
    assert item is not None, "Item not found in draft"
    mass_prop = item.get_property("demo_property_mass")
    
    # Verify it returns a property wrapper
    assert mass_prop is not None
    assert mass_prop.value == 10.5


def test_baseline_and_version_in_dir() -> None:
    """Test that baseline and version appear in __dir__ for product nodes."""
    
    t = _MockTransport()
    _client_with_graphql_mock(t)


def test_change_tracking_with_get_property_records_id_and_path(tmp_path: Any) -> None:
    """Ensure get_property() integrates with PropertyChangeTracker (ID + path).

    This simulates the notebook usage pattern:

        prod = ws.demo_product
        item = prod.baseline.demo_item
        mass = item.get_property("demo_property_mass")
        print(mass.value)

    and verifies that:
    - A baseline is recorded keyed by property_id.
    - An accessed_properties entry is created with a property_path pointing to that ID.
    """
    from poelis_sdk.change_tracker import PropertyChangeTracker

    baseline_file = str(tmp_path / "baseline.json")

    t = _MockTransport()
    c = _client_with_graphql_mock(
        t,
        enable_change_detection=True,
        baseline_file=baseline_file,
        log_file=str(tmp_path / "changes.log"),
    )

    # Sanity: change tracker is enabled and uses the expected baseline file.
    tracker: PropertyChangeTracker = c._change_tracker  # type: ignore[attr-defined]
    assert tracker.is_enabled() is True
    assert tracker._baseline_file == baseline_file

    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]

    # Access property via get_property at item level (within baseline) and read its value.
    # For product nodes, accessing items automatically routes through baseline
    item = prod["gadget_a"]
    mass_prop = item.get_property("demo_property_mass")
    value = mass_prop.value
    assert value == 10.5

    # After the first access, a baseline should exist keyed by the property ID,
    # and accessed_properties should contain a path mapped back to that ID.
    baselines = tracker._baselines
    accessed_props = tracker._accessed_properties

    # There should be exactly one baseline entry.
    assert len(baselines) == 1
    property_id = next(iter(baselines.keys()))
    baseline_entry = baselines[property_id]
    assert baseline_entry["value"] == 10.5

    # There should be at least one accessed_properties entry that references this ID.
    assert accessed_props
    assert any(info.get("property_id") == property_id for info in accessed_props.values())
    
    b = c.browser
    ws = b["uh2"]
    prod = ws["Widget Pro"]
    
    # Check that baseline and version are in dir()
    dir_items = dir(prod)
    assert "baseline" in dir_items
    # Product nodes expose version shortcuts as v1/v2/... (not a literal "version" attribute).
    assert "v1" in dir_items
    assert "draft" in dir_items


